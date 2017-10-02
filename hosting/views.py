import re
from datetime import date

from django.db.models import Q
from django.contrib.gis.db.models.functions import Distance
from django.views import generic
from django.conf import settings
from django.db import models
from django.http import QueryDict, HttpResponseRedirect, Http404, JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.vary import vary_on_headers
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import get_template
from django.template import Context
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils.six.moves.urllib.parse import unquote_plus
from django.utils.http import urlquote_plus
from django.utils.encoding import uri_to_iri
from django.utils import timezone

from django_countries.fields import Country
from .models import Profile, Place, Phone

from braces.views import FormInvalidMessageMixin
from core.auth import AuthMixin, PERM_SUPERVISOR, SUPERVISOR, OWNER, VISITOR, ANONYMOUS
from core.mixins import LoginRequiredMixin
from .utils import geocode
from .mixins import (
    ProfileModifyMixin, ProfileIsUserMixin,
    PhoneMixin, PlaceMixin, FamilyMemberMixin, FamilyMemberAuthMixin,
    CreateMixin, UpdateMixin, DeleteMixin,
)
from core.forms import UserRegistrationForm
from core.models import SiteConfiguration
from .forms import (
    ProfileForm, ProfileCreateForm, ProfileEmailUpdateForm,
    PhoneForm, PhoneCreateForm,
    PlaceForm, PlaceCreateForm, PlaceBlockForm, PlaceLocationForm,
    FamilyMemberForm, FamilyMemberCreateForm,
    UserAuthorizeForm, UserAuthorizedOnceForm,
)

User = get_user_model()
lang = settings.LANGUAGE_CODE



class ProfileCreateView(LoginRequiredMixin, ProfileModifyMixin, FormInvalidMessageMixin, generic.CreateView):
    model = Profile
    form_class = ProfileCreateForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def dispatch(self, request, *args, **kwargs):
        try:
            # Redirect to profile edit page if user is logged in & profile already exists.
            return HttpResponseRedirect(self.request.user.profile.get_edit_url(), status=301)
        except Profile.DoesNotExist:
            return super().dispatch(request, *args, **kwargs)
        except AttributeError:
            # Redirect to registration page when user is not authenticated.
            return HttpResponseRedirect(reverse_lazy('register'), status=303)

    def get_form(self, form_class=ProfileCreateForm):
        return form_class(user=self.request.user, **self.get_form_kwargs())

profile_create = ProfileCreateView.as_view()


class ProfileUpdateView(UpdateMixin, AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, FormInvalidMessageMixin, generic.UpdateView):
    model = Profile
    form_class = ProfileForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

profile_update = ProfileUpdateView.as_view()


class ProfileDeleteView(DeleteMixin, AuthMixin, ProfileIsUserMixin, generic.DeleteView):
    model = Profile
    form_class = ProfileForm
    success_url = reverse_lazy('logout')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['places'] = self.object.owned_places.filter(deleted=False)
        return context

    def get_success_url(self):
        # Administrators will be redirected to the deleted profile's page.
        if self.role >= SUPERVISOR:
            return self.object.get_absolute_url()
        return self.success_url

    def get_failure_url(self):
        return reverse_lazy('profile_settings', kwargs={
            'pk': self.object.pk, 'slug': slugify(self.object.user.username)})

    def delete(self, request, *args, **kwargs):
        """
        Set the flag 'deleted' to True on the profile and some associated objects,
        deactivate the linked user,
        and then redirect to the success URL.
        """
        now = timezone.now()
        self.object = self.get_object()
        if not self.object.deleted:
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
        return super().delete(request, *args, **kwargs)

profile_delete = ProfileDeleteView.as_view()


class ProfileRedirectView(LoginRequiredMixin, generic.RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if kwargs.get('pk', None):
            profile = get_object_or_404(Profile, pk=kwargs['pk'])
            if profile.user:
                return profile.get_absolute_url()
            else:
                raise Http404("Detached profile (probably a family member).")
        try:
            return self.request.user.profile.get_edit_url()
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')

profile_redirect = ProfileRedirectView.as_view()


class ProfileDetailView(AuthMixin, ProfileIsUserMixin, generic.DetailView):
    model = Profile
    public_view = True
    minimum_role = VISITOR

    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if profile.deleted and self.role == VISITOR and not self.request.user.has_perm(PERM_SUPERVISOR):
            raise Http404("Profile was deleted.")
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['places'] = self.object.owned_places.filter(deleted=False)
        context['phones'] = self.object.phones.filter(deleted=False)
        return context

profile_detail = ProfileDetailView.as_view()


class ProfileEditView(ProfileDetailView):
    template_name = 'hosting/profile_edit.html'
    public_view = False
    minimum_role = OWNER

profile_edit = ProfileEditView.as_view()


class ProfileSettingsView(ProfileDetailView):
    template_name = 'hosting/settings.html'
    minimum_role = OWNER

    @property
    def profile_email_help_text(self):
        return Profile._meta.get_field('email').help_text

profile_settings = ProfileSettingsView.as_view()


class ProfileEmailUpdateView(AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, generic.UpdateView):
    model = Profile
    template_name = 'hosting/profile-email_form.html'
    form_class = ProfileEmailUpdateForm
    minimum_role = OWNER

profile_email_update = ProfileEmailUpdateView.as_view()


class PlaceCreateView(CreateMixin, AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, FormInvalidMessageMixin, generic.CreateView):
    model = Place
    form_class = PlaceCreateForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.create_for
        return kwargs

place_create = PlaceCreateView.as_view()


class PlaceUpdateView(UpdateMixin, AuthMixin, PlaceMixin, ProfileModifyMixin, FormInvalidMessageMixin, generic.UpdateView):
    form_class = PlaceForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")

    def form_valid(self, form):
        response = super().form_valid(form)
        if '_gotomap' in self.request.POST or form.confidence < 8:
            map_url = reverse_lazy('place_location_update', kwargs={'pk': self.object.pk})
            return HttpResponseRedirect(map_url)
        return response

place_update = PlaceUpdateView.as_view()


class PlaceLocationUpdateView(UpdateMixin, AuthMixin, PlaceMixin, generic.UpdateView):
    form_class = PlaceLocationForm

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('place_detail_verbose', kwargs={'pk': self.object.pk})

place_location_update = PlaceLocationUpdateView.as_view()


class PlaceDeleteView(DeleteMixin, AuthMixin, PlaceMixin, ProfileModifyMixin, generic.DeleteView):
    pass

place_delete = PlaceDeleteView.as_view()


class PlaceDetailView(AuthMixin, PlaceMixin, generic.DetailView):
    """
    View with details about a place; allows also anonymous (unauthenticated) user access.
    For such users, the registration form will be displayed.
    """
    model = Place
    minimum_role = ANONYMOUS
    verbose_view = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['register_form'] = UserRegistrationForm
        context['blocking'] = self.calculate_blocking(self.object)
        return context

    @staticmethod
    def calculate_blocking(place):
        block = {}
        today = date.today()
        if place.is_blocked:
            block['enabled'] = True
            if place.blocked_from and place.blocked_from > today:
                block['display_from'] = True
                block['format_from'] = "MONTH_DAY_FORMAT" if place.blocked_from.year == today.year else "DATE_FORMAT"
            if place.blocked_until and place.blocked_until >= today:
                block['display_until'] = True
                block['format_until'] = "MONTH_DAY_FORMAT" if place.blocked_until.year == today.year else "DATE_FORMAT"
        else:
            block['enabled'] = False
        block['form'] = PlaceBlockForm(instance=place)
        return block

    def render_to_response(self, context, **response_kwargs):
        # Automatically redirect the user to the verbose view if permission granted (in authorized_users list).
        is_authorized = self.request.user in self.object.authorized_users.all()
        is_supervisor = self.role >= SUPERVISOR
        if is_authorized and not is_supervisor and not isinstance(self, PlaceDetailVerboseView):
            return HttpResponseRedirect(reverse_lazy('place_detail_verbose', kwargs={'pk': self.kwargs['pk']}))
        else:
            return super().render_to_response(context)

place_detail = PlaceDetailView.as_view()


class PlaceDetailVerboseView(PlaceDetailView):
    verbose_view = True

    def render_to_response(self, context, **response_kwargs):
        # Automatically redirect the user to the scarce view if permission to details not granted.
        user = self.request.user
        is_authorized = user in self.object.authorized_users.all()
        is_family_member = getattr(user, 'profile', None) in self.object.family_members.all()
        self.__dict__.setdefault('debug', {}).update(
            {'authorized': is_authorized, 'family member': is_family_member}
        )
        if self.role >= OWNER or is_authorized or is_family_member:
            return super().render_to_response(context)
        else:
            return HttpResponseRedirect(reverse_lazy('place_detail', kwargs={'pk': self.kwargs['pk']}))

    def get_debug_data(self):
        return self.debug

place_detail_verbose = PlaceDetailVerboseView.as_view()


class PlaceBlockView(AuthMixin, PlaceMixin, generic.View):
    http_method_names = ['put']
    exact_role = OWNER

    def put(self, request, *args, **kwargs):
        place = self.get_object()
        if place.deleted:
            return JsonResponse({'result': False, 'err': {'__all__': [_("Deleted place"),]}})
        form = PlaceBlockForm(data=QueryDict(request.body), instance=place)
        data_correct = form.is_valid()
        viewresponse = {'result': data_correct}
        if data_correct:
            form.save()
        else:
            viewresponse.update({'err': form.errors})
        return JsonResponse(viewresponse)

place_block = PlaceBlockView.as_view()


class PhoneCreateView(CreateMixin, AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, generic.CreateView):
    model = Phone
    form_class = PhoneCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.create_for
        return kwargs

phone_create = PhoneCreateView.as_view()


class PhoneUpdateView(UpdateMixin, AuthMixin, PhoneMixin, ProfileModifyMixin, generic.UpdateView):
    form_class = PhoneForm

phone_update = PhoneUpdateView.as_view()


class PhoneDeleteView(DeleteMixin, AuthMixin, PhoneMixin, ProfileModifyMixin, generic.DeleteView):
    pass

phone_delete = PhoneDeleteView.as_view()


class InfoConfirmView(LoginRequiredMixin, generic.View):
    """Allows the current user (only) to confirm their profile and accommodation details as up-to-date."""
    http_method_names = ['post']
    template_name = 'links/confirmed.html'

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        try:
            request.user.profile.confirm_all_info()
            if request.is_ajax():
                return JsonResponse({'success': 'confirmed'})
            else:
                return TemplateResponse(request, self.template_name)
        except Profile.DoesNotExist:
            return HttpResponseRedirect(reverse_lazy('profile_create'))

hosting_info_confirm = InfoConfirmView.as_view()


class PlaceCheckView(AuthMixin, PlaceMixin, generic.View):
    """Allows a supervisor to confirm accommodation details of a user as up-to-date."""
    http_method_names = ['post']
    template_name = '404.html'
    minimum_role = SUPERVISOR

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        self.get_object().set_check_status(self.request.user)
        if request.is_ajax():
            return JsonResponse({'success': 'checked'})
        else:
            # Not implemented; only AJAX requests are expected.
            return TemplateResponse(request, self.template_name)

place_check = PlaceCheckView.as_view()


class PlaceListView(generic.ListView):
    model = Place

place_list = PlaceListView.as_view()


class PlaceStaffListView(AuthMixin, PlaceListView):
    """A place for supervisors to see an overview of and manage hosts in their area of responsibility."""
    template_name = "hosting/place_list_supervisor.html"
    minimum_role = SUPERVISOR

    def dispatch(self, request, *args, **kwargs):
        self.country = Country(kwargs['country_code'])
        kwargs['auth_base'] = self.country
        self.in_book = {'0': False, '1': True, None: None}[kwargs['in_book']]
        self.invalid_emails = kwargs['email']
        return super().dispatch(request, *args, **kwargs)

    def get_owner(self, object):
        return None

    def get_location(self, object):
        return object

    def get_queryset(self):
        self.base_qs = self.model.available_objects.filter(country=self.country.code)
        if self.in_book is not None:
            qs = self.base_qs.filter(in_book=self.in_book)
        else:
            qs = self.base_qs
        if self.invalid_emails:
            qs = qs.filter(owner__user__email__startswith=settings.INVALID_PREFIX)
        return qs.prefetch_related('owner__user', 'owner__phones').order_by('-confirmed', 'checked', 'owner__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['in_book_count'] = self.base_qs.filter(in_book=True).count()
        context['not_in_book_count'] = self.base_qs.filter(in_book=False).count()
        if self.in_book is not None:
            book_filter = models.Q(in_book=self.in_book)
            context['place_count'] = context['in_book_count'] if self.in_book else context['not_in_book_count']
        else:
            book_filter = models.Q()
            context['place_count'] = context['in_book_count'] + context['not_in_book_count']
        context['checked_count'] = self.base_qs.filter(book_filter, checked=True).count()
        context['confirmed_count'] = self.base_qs.filter(book_filter, confirmed=True).count()
        context['not_confirmed_count'] = context['place_count'] - context['confirmed_count']
        context['invalid_emails_count'] = self.base_qs.filter(
            owner__user__email__startswith=settings.INVALID_PREFIX).count()
        return context

staff_place_list = PlaceStaffListView.as_view()


class SearchView(PlaceListView):
    queryset = Place.objects.filter(available=True)
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        if 'ps_q' in request.GET:
            # Keeping Unicode in URL, replacing space with '+'.
            query = uri_to_iri(urlquote_plus(request.GET['ps_q']))
            params = {'query': query} if query else None
            return HttpResponseRedirect(reverse_lazy('search', kwargs=params))
        query = kwargs['query'] or ''  # Avoiding query=None
        self.query = unquote_plus(query)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        self.result = geocode(self.query)
        if self.query and self.result.point:
            if not self.result.state:  # We assume it's a country
                return (self.queryset.filter(country=self.result.country.upper())
                                     .order_by('owner__user__last_login'))
            return (self.queryset.annotate(distance=Distance('location', self.result.point))
                                 .order_by('distance'))
        return self.queryset.order_by('owner__user__last_login')

    def get_detail_queryset(self):
        if len(self.query) <= 3:
            return self.queryset
        lookup = (
            Q(owner__user__username__icontains=self.query) |
            Q(owner__first_name__icontains=self.query) |
            Q(owner__last_name__icontains=self.query) |
            Q(closest_city__icontains=self.query)
        )
        return self.queryset.filter(lookup).select_related('owner__user')

    @property
    def get_query(self):
        return self.query


search = SearchView.as_view()


class UserAuthorizeView(AuthMixin, generic.FormView):
    """Form view to add a user to the list of authorized users for a place to be able to see more details."""
    template_name = 'hosting/place_authorized_users.html'
    form_class = UserAuthorizeForm
    exact_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        self.place = get_object_or_404(Place, pk=self.kwargs['pk'])
        kwargs['auth_base'] = self.place
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['place'] = self.place
        m = re.match(r'^/([a-zA-Z]+)/', self.request.GET.get('next', default=''))
        if m:
            context['back_to'] = m.group(1).lower()
        def order_by_name(user):
            try:
                return (" ".join((user.profile.first_name, user.profile.last_name)).strip() or user.username).lower()
            except Profile.DoesNotExist:
                return user.username.lower()
        context['authorized_set'] = [(user, UserAuthorizedOnceForm(initial={'user': user.pk}, auto_id=False))
                                     for user
                                     in sorted(self.place.authorized_users.all(), key=order_by_name)]
        return context

    def form_valid(self, form):
        if not form.cleaned_data['remove']:
            # For addition, "user" is the username.
            user = get_object_or_404(User, username=form.cleaned_data['user'])
            if user not in self.place.authorized_users.all():
                self.place.authorized_users.add(user)
                if not user.email.startswith(settings.INVALID_PREFIX):
                    self.send_email(user, self.place)
        else:
            # For removal, "user" is the primary key.
            user = get_object_or_404(User, pk=form.cleaned_data['user'])
            self.place.authorized_users.remove(user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('authorize_user', kwargs={'pk': self.kwargs['pk']})

    def send_email(self, user, place):
        config = SiteConfiguration.get_solo()
        subject = _("[Pasporta Servo] You received an Authorization")
        email_template_text = get_template('email/new_authorization.txt')
        email_template_html = get_template('email/new_authorization.html')
        email_context = Context({
            'site_name': config.site_name,
            'user': user,
            'place': place,
        })
        send_mail(
            subject,
            email_template_text.render(email_context),
            settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=email_template_html.render(email_context),
            fail_silently=False,
        )

authorize_user = UserAuthorizeView.as_view()


class FamilyMemberCreateView(CreateMixin, AuthMixin, FamilyMemberMixin, generic.CreateView):
    model = Profile
    form_class = FamilyMemberCreateForm

    def verify_anonymous_family(self):
        # Allow creation of only one completely anonymous family member.
        if self.place.family_members.count() == 1 and not self.place.family_members.first().full_name.strip():
            return HttpResponseRedirect(
                reverse_lazy('family_member_update',
                    kwargs={'pk': self.place.family_members.first().pk, 'place_pk': self.kwargs['place_pk']}))
        else:
            return None

    def get(self, request, *args, **kwargs):
        redirect = self.verify_anonymous_family()
        return redirect or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        redirect = self.verify_anonymous_family()
        return redirect or super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs

family_member_create = FamilyMemberCreateView.as_view()


class FamilyMemberUpdateView(UpdateMixin, AuthMixin, FamilyMemberAuthMixin, FamilyMemberMixin, generic.UpdateView):
    model = Profile
    form_class = FamilyMemberForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs

family_member_update = FamilyMemberUpdateView.as_view()


class FamilyMemberRemoveView(AuthMixin, FamilyMemberMixin, generic.DeleteView):
    """Remove the family member for the Place."""
    model = Profile
    template_name = 'hosting/family_member_confirm_delete.html'
    minimum_role = OWNER

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.place.family_members.remove(self.object)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['place'] = self.place
        return context

family_member_remove = FamilyMemberRemoveView.as_view()


class FamilyMemberDeleteView(DeleteMixin, AuthMixin, FamilyMemberAuthMixin, FamilyMemberMixin, generic.DeleteView):
    """Remove the family member for the Place and delete it."""
    model = Profile

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.other_places.count() > 0:
            raise Http404("This family member is listed at other places as well; cannot delete the profile.")
        return self.object

    def delete(self, request, *args, **kwargs):
        redirect = super().delete(request, *args, **kwargs)
        self.place.family_members.remove(self.object)
        return redirect

family_member_delete = FamilyMemberDeleteView.as_view()
