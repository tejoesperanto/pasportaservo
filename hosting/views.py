import re

import geopy

from django.views import generic
from django.conf import settings
from django.http import HttpResponseRedirect, Http404, JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.vary import vary_on_headers
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import linebreaks as tohtmlpara, urlize
from django.utils.six.moves.urllib.parse import unquote_plus
from django.utils.http import urlquote_plus
from django.utils.encoding import uri_to_iri
from django.utils import timezone

from rest_framework import viewsets
from braces.views import LoginRequiredMixin, UserPassesTestMixin, FormInvalidMessageMixin
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from django_countries.fields import Country

from core.forms import UserRegistrationForm
from .models import Profile, Place, Phone, SUPERVISOR
from .serializers import ProfileSerializer, PlaceSerializer, UserSerializer
from .mixins import (
    ProfileMixin, ProfileAuthMixin, PlaceAuthMixin, PhoneAuthMixin,
    FamilyMemberMixin, FamilyMemberAuthMixin,
    SupervisorMixin, CreateMixin, DeleteMixin,
)
from .forms import (
    AuthorizeUserForm, AuthorizedOnceUserForm,
    ProfileForm, ProfileCreateForm, PhoneForm, PhoneCreateForm,
    PlaceForm, PlaceCreateForm, FamilyMemberForm, FamilyMemberCreateForm,
    EmailUpdateForm,
)


User = get_user_model()
lang = settings.LANGUAGE_CODE


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    http_method_names = ['get']


class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    http_method_names = ['get']


class PlaceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows places to be viewed or edited.
    """
    serializer_class = PlaceSerializer
    queryset = Place.with_coord.all()
    http_method_names = ['get']

    def get_queryset(self):
        qs = self.queryset
        qs = self.get_serializer_class().setup_eager_loading(qs)
        bounds = {p: self.request.query_params.get(p, None) for p in 'nswe'}
        if any(bounds.values()):
            qs = qs.filter(latitude__range=(bounds['s'], bounds['n']))
            qs = qs.filter(longitude__range=(bounds['w'], bounds['e']))
        return qs


class ProfileCreateView(LoginRequiredMixin, ProfileMixin, FormInvalidMessageMixin, generic.CreateView):
    model = Profile
    form_class = ProfileCreateForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def dispatch(self, request, *args, **kwargs):
        try:
            # Redirect to profile edit page if user is logged in & profile already exists.
            return HttpResponseRedirect(self.request.user.profile.get_edit_url(), status=301)
        except Profile.DoesNotExist:
            return super(ProfileCreateView, self).dispatch(request, *args, **kwargs)
        except AttributeError:
            # Redirect to registration page when user is not authenticated.
            return HttpResponseRedirect(reverse_lazy('register'), status=303)

    def get_form(self, form_class=ProfileCreateForm):
        user = self.request.user
        return form_class(user=user, **self.get_form_kwargs())

profile_create = ProfileCreateView.as_view()


class ProfileUpdateView(LoginRequiredMixin, ProfileMixin, ProfileAuthMixin, FormInvalidMessageMixin, generic.UpdateView):
    form_class = ProfileForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def form_valid(self, form):
        self.object.checks(self.request)
        return super(ProfileUpdateView, self).form_valid(form)

profile_update = ProfileUpdateView.as_view()


class ProfileDeleteView(LoginRequiredMixin, DeleteMixin, ProfileAuthMixin, generic.DeleteView):
    form_class = ProfileForm
    success_url = reverse_lazy('logout')

    def get_object(self, queryset=None):
        object = super(ProfileDeleteView, self).get_object(queryset)
        if not object.user:
            raise Http404("Detached profile (probably a family member).")
        return object

    def get_context_data(self, **kwargs):
        context = super(ProfileDeleteView, self).get_context_data(**kwargs)
        context['places'] = self.object.owned_places.filter(deleted=False)
        return context

    def get_success_url(self):
        # Administrators will be redirected to the deleted profile's page.
        if self.object.user != self.request.user:
            return self.object.get_absolute_url()
        return self.success_url

    def delete(self, request, *args, **kwargs):
        """
        Set the flag 'deleted' to True on the profile and some associated objects,
        deactivate the linked user,
        and then redirect to the success URL.
        """
        now = timezone.now()
        self.object = self.get_object()
        for place in self.object.owned_places.all():
            place.deleted_on = now
            place.save()
            for member in place.family_members.all():
                if not member.user:
                    member.deleted_on = now
                    member.save()
        self.object.phones.all().delete()
        self.object.user.is_active = False
        self.object.user.save()
        return super(ProfileDeleteView, self).delete(request, *args, **kwargs)

profile_delete = ProfileDeleteView.as_view()


class ProfileRedirectView(LoginRequiredMixin, generic.RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if kwargs.get('pk', None):
            return get_object_or_404(Profile, pk=kwargs['pk']).get_absolute_url()
        try:
            return self.request.user.profile.get_edit_url()
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')

profile_redirect = ProfileRedirectView.as_view()


class ProfileDetailView(LoginRequiredMixin, ProfileAuthMixin, generic.DetailView):
    model = Profile
    public_view = True

    def get_context_data(self, **kwargs):
        context = super(ProfileDetailView, self).get_context_data(**kwargs)
        context['places'] = self.object.owned_places.filter(deleted=False)
        context['phones'] = self.object.phones.filter(deleted=False)
        context['role'] = self.role
        return context

profile_detail = ProfileDetailView.as_view()


class ProfileEditView(ProfileDetailView):
    template_name = 'hosting/profile_edit.html'
    public_view = False

profile_edit = ProfileEditView.as_view()


class ProfileSettingsView(ProfileDetailView):
    template_name = 'hosting/settings.html'

    @property
    def profile_email_help_text(self):
        return Profile._meta.get_field('email').help_text

profile_settings = ProfileSettingsView.as_view()


class PlaceCreateView(LoginRequiredMixin, ProfileMixin, FormInvalidMessageMixin, CreateMixin, generic.CreateView):
    model = Place
    form_class = PlaceCreateForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def get_form_kwargs(self):
        kwargs = super(PlaceCreateView, self).get_form_kwargs()
        kwargs['profile'] = get_object_or_404(Profile, pk=self.kwargs['pk'])
        return kwargs

place_create = PlaceCreateView.as_view()


class PlaceUpdateView(LoginRequiredMixin, ProfileMixin, PlaceAuthMixin, FormInvalidMessageMixin, generic.UpdateView):
    form_class = PlaceForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def form_valid(self, form):
        self.object.checked = self.object.owner.user != self.request.user
        self.object.checked_by = self.request.user if self.object.checked else None
        self.object.save()
        return super(PlaceUpdateView, self).form_valid(form)

place_update = PlaceUpdateView.as_view()


class PlaceDeleteView(LoginRequiredMixin, DeleteMixin, ProfileMixin, PlaceAuthMixin, generic.DeleteView):
    pass

place_delete = PlaceDeleteView.as_view()


class PlaceDetailView(generic.DetailView):
    model = Place
    verbose_view = False

    def get_context_data(self, **kwargs):
        context = super(PlaceDetailView, self).get_context_data(**kwargs)
        context['form'] = UserRegistrationForm
        return context

    def render_to_response(self, context, **response_kwargs):
        # Automatically redirect the user to the verbose view if permission granted (in authorized_users list).
        if (self.request.user in self.object.authorized_users.all() and not self.request.user.is_staff
            and not isinstance(self, PlaceDetailVerboseView)):
            return HttpResponseRedirect(reverse_lazy('place_detail_verbose', kwargs={'pk': self.kwargs['pk']}))
        else:
            return super(PlaceDetailView, self).render_to_response(context)

place_detail = PlaceDetailView.as_view()


class PlaceDetailVerboseView(UserPassesTestMixin, PlaceDetailView):
    redirect_field_name = ''
    redirect_unauthenticated_users = True
    verbose_view = True

    def get_login_url(self):
        return reverse_lazy('place_detail', kwargs={'pk': self.kwargs['pk']})

    def test_func(self, user):
        object = self.get_object()
        return (user is not None and user.is_authenticated()
                and (user.is_staff or user in object.authorized_users.all() or user.profile == object.owner))

place_detail_verbose = PlaceDetailVerboseView.as_view()


class PhoneCreateView(LoginRequiredMixin, ProfileMixin, CreateMixin, generic.CreateView):
    model = Phone
    form_class = PhoneCreateForm

    def get_form_kwargs(self):
        kwargs = super(PhoneCreateView, self).get_form_kwargs()
        kwargs['profile'] = get_object_or_404(Profile, pk=self.kwargs['pk'])
        return kwargs

phone_create = PhoneCreateView.as_view()


class PhoneUpdateView(LoginRequiredMixin, ProfileMixin, PhoneAuthMixin, generic.UpdateView):
    form_class = PhoneForm

phone_update = PhoneUpdateView.as_view()


class PhoneDeleteView(LoginRequiredMixin, ProfileMixin, PhoneAuthMixin, generic.DeleteView):
    pass

phone_delete = PhoneDeleteView.as_view()


class ConfirmInfoView(LoginRequiredMixin, generic.View):
    http_method_names = ['post']
    template_name = 'links/confirmed.html'

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        request.user.profile.confirm_all_info()
        if request.is_ajax():
            return JsonResponse({'success': 'confirmed'})
        else:
            return TemplateResponse(request, self.template_name)

confirm_hosting_info = ConfirmInfoView.as_view()


class PlaceCheckView(LoginRequiredMixin, PlaceAuthMixin, generic.View):
    http_method_names = ['post']
    minimum_role = SUPERVISOR
    template_name = '404.html'

    def post(self, request, *args, **kwargs):
        self.get_object().checks(self.request)
        if request.is_ajax():
            return JsonResponse({'success': 'checked'})
        else:  # Not tested/implemented
            return TemplateResponse(request, self.template_name)

place_check = PlaceCheckView.as_view()


class PlaceListView(generic.ListView):
    model = Place

place_list = PlaceListView.as_view()


class CountryPlaceListView(LoginRequiredMixin, SupervisorMixin, PlaceListView):
    template_name = "hosting/place_list_supervisor.html"

    def dispatch(self, request, *args, **kwargs):
        self.country_code = self.kwargs['country_code']
        self.country = Country(self.country_code)
        self.in_book = {'0': False, '1': True, None: True}[kwargs['in_book']]
        self.invalid_emails = kwargs['email']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.base_qs = self.model.available_objects.filter(country=self.country_code)
        qs = self.base_qs.filter(in_book=self.in_book)
        if self.invalid_emails:
            qs = qs.filter(owner__user__email__startswith=settings.INVALID_PREFIX)
        return qs.prefetch_related('owner__user', 'owner__phones').order_by('-confirmed', 'checked', 'owner__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['in_book_count'] = self.base_qs.filter(in_book=True).count()
        context['not_in_book_count'] = self.base_qs.filter(in_book=False).count()
        context['place_count'] = self.base_qs.filter(in_book=self.in_book).count()
        context['checked_count'] = self.base_qs.filter(in_book=self.in_book, checked=True).count()
        context['confirmed_count'] = self.base_qs.filter(in_book=self.in_book, confirmed_on__isnull=False).count()
        context['not_confirmed_count'] = context['place_count'] - context['confirmed_count']
        context['invalid_emails_count'] = self.base_qs.filter(
            owner__user__email__startswith=settings.INVALID_PREFIX).count()
        return context

country_place_list = CountryPlaceListView.as_view()


class SearchView(PlaceListView):

    def first_with_bounds(self, locations):
        for location in locations:
            if 'bounds' in location.raw:
                return location

    def get(self, request, *args, **kwargs):
        if 'ps_q' in request.GET:
            # Keeping Unicode in URL, replacing space with '+'
            query = uri_to_iri(urlquote_plus(request.GET['ps_q']))
            params = {'query': query} if query else None
            return HttpResponseRedirect(reverse_lazy('search', kwargs=params))
        query = kwargs['query'] or ''  # Avoiding query=None
        self.query = unquote_plus(query)
        if self.query:
            try:
                geocoder = geopy.geocoders.OpenCage(settings.OPENCAGE_KEY, timeout=5)
                self.locations = geocoder.geocode(self.query, language=lang, exactly_one=False)
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                self.locations = []
        return super(SearchView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        """Find location by bounding box. Filters also by country,
        because some bbox for some countres are huge (e.g. France, USA).
        """
        qs = Place.objects.none()
        if self.query and self.locations:
            location = self.first_with_bounds(self.locations)
            if location:
                country_code = location.raw['components'].get('country_code')
                bounds = location.raw['bounds']
                lats = (bounds['southwest']['lat'], bounds['northeast']['lat'])
                lngs = (bounds['southwest']['lng'], bounds['northeast']['lng'])
                qs = Place.objects.filter(available=True)
                qs = qs.filter(latitude__range=lats, longitude__range=lngs)
                qs = qs.filter(country=country_code.upper()) if country_code else qs

        """Search in the Profile name and username too."""
        if len(self.query) <= 3:
            return qs
        qs |= Place.objects.filter(owner__user__username__icontains=self.query)
        qs |= Place.objects.filter(owner__first_name__icontains=self.query)
        qs |= Place.objects.filter(owner__last_name__icontains=self.query)
        qs |= Place.objects.filter(closest_city__icontains=self.query)
        return qs.select_related('owner__user').order_by('country', 'city')

    @property
    def get_query(self):
        return self.query

search = SearchView.as_view()


class AuthorizeUserView(LoginRequiredMixin, generic.FormView):
    """Form view to add a user to the list of authorized users
    for a place to be able to see more details."""
    template_name = 'hosting/place_authorized_users.html'
    form_class = AuthorizeUserForm

    def dispatch(self, request, *args, **kwargs):
        self.place = get_object_or_404(Place,
                                       pk=self.kwargs['pk'],
                                       owner__user_id=self.request.user.pk)
        return super(AuthorizeUserView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AuthorizeUserView, self).get_context_data(**kwargs)
        context['place'] = self.place
        m = re.match(r'^/([a-zA-Z]+)/', self.request.GET.get('next', default=''))
        if m:
            context['back_to'] = m.group(1).lower()
        def order_by_name(user):
            try:
                return (" ".join((user.profile.first_name, user.profile.last_name)).strip() or user.username).lower()
            except Profile.DoesNotExist:
                return user.username.lower()
        context['authorized_set'] = [(user, AuthorizedOnceUserForm(initial={'user': user.pk}, auto_id=False))
                                     for user
                                     in sorted(self.place.authorized_users.all(), key=order_by_name)]
        return context

    def form_valid(self, form):
        if not form.cleaned_data['remove']:
            # for addition, "user" is the username
            user = get_object_or_404(User, username=form.cleaned_data['user'])
            if user not in self.place.authorized_users.all():
                self.place.authorized_users.add(user)
                self.send_email(user, self.place)
        else:
            # for removal, "user" is the primary key
            user = get_object_or_404(User, pk=form.cleaned_data['user'])
            self.place.authorized_users.remove(user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('authorize_user', kwargs={'pk': self.kwargs['pk']})

    def send_email(self, user, place):
        subject = _("[Pasporta Servo] You received an Authorization")
        to = [user.email]
        email_template_text = 'hosting/emails/new_authorization.txt'
        email_template_html = 'hosting/emails/mail_template.html'
        email_context = {
            'user_first_name': user.profile.name,
            'owner_name': place.owner.full_name,
            'place_id': place.pk,
            'place_address': str(place),
            'site_domain': self.request.get_host(),
            'site_name': settings.SITE_NAME,
        }
        message_text = render_to_string(email_template_text, email_context)
        message_html = render_to_string(email_template_html, {'body': mark_safe(tohtmlpara(urlize(message_text))),})

        message = EmailMultiAlternatives(subject, message_text, to=to)
        message.attach_alternative(message_html, 'text/html')
        message.send()

authorize_user = AuthorizeUserView.as_view()


class FamilyMemberCreateView(LoginRequiredMixin, CreateMixin, FamilyMemberMixin, generic.CreateView):
    model = Profile
    form_class = FamilyMemberCreateForm

    def verify_anonymous_family(self):
        # Allow creation of only one completely anonymous family member.
        if self.place.family_members.count() == 1 and not self.place.family_members.all()[0].full_name.strip():
            return HttpResponseRedirect(
                reverse_lazy('family_member_update',
                    kwargs={'pk': self.place.family_members.all()[0].pk, 'place_pk': self.kwargs['place_pk']}))
        else:
            return None

    def get(self, request, *args, **kwargs):
        redirect = self.verify_anonymous_family()
        return redirect or super(FamilyMemberCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        redirect = self.verify_anonymous_family()
        return redirect or super(FamilyMemberCreateView, self).post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(FamilyMemberCreateView, self).get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs

family_member_create = FamilyMemberCreateView.as_view()


class FamilyMemberUpdateView(LoginRequiredMixin, FamilyMemberAuthMixin, FamilyMemberMixin, generic.UpdateView):
    model = Profile
    form_class = FamilyMemberForm

    def get_form_kwargs(self):
        kwargs = super(FamilyMemberUpdateView, self).get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs

family_member_update = FamilyMemberUpdateView.as_view()


class FamilyMemberRemoveView(LoginRequiredMixin, FamilyMemberMixin, generic.DeleteView):
    """Remove the family member for the Place."""
    model = Profile
    template_name = 'hosting/family_member_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.place.family_members.remove(self.object)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(FamilyMemberRemoveView, self).get_context_data(**kwargs)
        context['place'] = self.place
        return context

family_member_remove = FamilyMemberRemoveView.as_view()


class FamilyMemberDeleteView(LoginRequiredMixin, DeleteMixin, FamilyMemberAuthMixin, FamilyMemberMixin, generic.DeleteView):
    """Remove the family member for the Place and delete it."""
    model = Profile

#    def get(self, request, *args, **kwargs):
#        pass

    def delete(self, request, *args, **kwargs):
        redirect = super(FamilyMemberDeleteView, self).delete(request, *args, **kwargs)
        self.object = self.get_object()
        self.place.family_members.remove(self.object)
        return redirect

family_member_delete = FamilyMemberDeleteView.as_view()


class EmailUpdateView(LoginRequiredMixin, ProfileMixin, ProfileAuthMixin, generic.UpdateView):
    model = User
    template_name = 'hosting/base_form.html'
    form_class = EmailUpdateForm

profile_email_update = EmailUpdateView.as_view()
