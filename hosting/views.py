import geopy

from django.views import generic
from django.conf import settings
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils.translation import ugettext_lazy as _

from braces.views import AnonymousRequiredMixin, LoginRequiredMixin
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from .models import Profile, Place, Phone
from .mixins import (ProfileMixin, ProfileAuthMixin, PlaceAuthMixin, PhoneAuthMixin,
    FamilyMemberMixin, DeleteMixin)
from .forms import (UserRegistrationForm, AuthorizeUserForm,
    ProfileForm, ProfileSettingsForm, ProfileCreateForm, PhoneForm, PhoneCreateForm,
    PlaceForm, PlaceCreateForm, FamilyMemberForm, FamilyMemberCreateForm)
from .utils import extend_bbox


User = get_user_model()
lang = settings.LANGUAGE_CODE


class HomeView(generic.TemplateView):
    template_name = 'hosting/home.html'

home = HomeView.as_view()


class RegisterView(AnonymousRequiredMixin, generic.CreateView):
    model = User
    template_name = 'registration/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile_create')
    authenticated_redirect_url = reverse_lazy('profile_detail')

    def form_valid(self, form):
        self.object = form.save()
        # Keeping this on ice; it interferes with the inline login, probably by wiping the session vars.
        result = super(RegisterView, self).form_valid(form)
        # Log in user
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1'])
        login(self.request, user)
        messages.success(self.request, "You are logged in.")
        return result

register = RegisterView.as_view()


class ProfileCreateView(LoginRequiredMixin, ProfileMixin, generic.CreateView):
    model = Profile
    form_class = ProfileCreateForm

    def get_form(self, form_class):
        user = self.request.user
        return form_class(user=user, **self.get_form_kwargs())

profile_create = ProfileCreateView.as_view()


class ProfileUpdateView(LoginRequiredMixin, ProfileMixin, ProfileAuthMixin, generic.UpdateView):
    form_class = ProfileForm

    def form_valid(self, form):
        self.object.checked = self.object.user != self.request.user
        self.object.save()
        return super(ProfileUpdateView, self).form_valid(form)

profile_update = ProfileUpdateView.as_view()


class ProfileDeleteView(LoginRequiredMixin, DeleteMixin, ProfileAuthMixin, generic.DeleteView):
    form_class = ProfileForm
    success_url = reverse_lazy('logout')

    def delete(self, request, *args, **kwargs):
        """
        Set the flag 'deleted' to True on the profile
        and some associated objects,
        desactivate the linked user,
        and then redirects to the success URL
        """
        self.object = self.get_object()
        for place in self.object.owned_places.all():
            place.deleted = True
            place.save()
            for member in place.family_members.all():
                if not member.user:
                    member.deleted = True
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
        return self.request.user.profile.get_absolute_url()

profile_redirect = ProfileRedirectView.as_view()


class ProfileDetailView(LoginRequiredMixin, ProfileAuthMixin, generic.DetailView):
    model = Profile
    public_view = True

    def get_context_data(self, **kwargs):
        context = super(ProfileDetailView, self).get_context_data(**kwargs)
        context['places'] = self.object.owned_places.all().filter(deleted=False)
        context['phones'] = self.object.phones.all().filter(deleted=False)
        context['role'] = self.role
        return context

profile_detail = ProfileDetailView.as_view()


class ProfileEditView(ProfileDetailView):
    template_name = 'hosting/profile_edit.html'
    public_view = False

profile_edit = ProfileEditView.as_view()


class ProfileSettingsView(LoginRequiredMixin, ProfileMixin, generic.UpdateView):
    model = User
    template_name = 'hosting/base_form.html'
    form_class = ProfileSettingsForm

    def get_object(self, queryset=None):
        return self.request.user

profile_settings = ProfileSettingsView.as_view()


class PlaceCreateView(LoginRequiredMixin, ProfileMixin, generic.CreateView):
    model = Place
    form_class = PlaceCreateForm

    def get_form_kwargs(self):
        kwargs = super(PlaceCreateView, self).get_form_kwargs()
        kwargs['profile'] = get_object_or_404(Profile, pk=self.kwargs['pk'])
        return kwargs

place_create = PlaceCreateView.as_view()


class PlaceUpdateView(LoginRequiredMixin, ProfileMixin, PlaceAuthMixin, generic.UpdateView):
    form_class = PlaceForm

    def form_valid(self, form):
        self.object.checked = self.object.owner.user != self.request.user
        self.object.save()
        return super(PlaceUpdateView, self).form_valid(form)

place_update = PlaceUpdateView.as_view()


class PlaceDeleteView(LoginRequiredMixin, DeleteMixin, ProfileMixin, PlaceAuthMixin, generic.DeleteView):
    pass

place_delete = PlaceDeleteView.as_view()


class PlaceDetailView(generic.DetailView):
    model = Place

    def get_context_data(self, **kwargs):
        context = super(PlaceDetailView, self).get_context_data(**kwargs)
        context['form'] = UserRegistrationForm
        return context

place_detail = PlaceDetailView.as_view()


class PhoneCreateView(LoginRequiredMixin, ProfileMixin, generic.CreateView):
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


class SearchView(generic.ListView):
    model = Place

    def get(self, request, *args, **kwargs):
        self.query = request.GET.get('q')
        if self.query:
            try:
                geocoder = geopy.geocoders.OpenCage(settings.OPENCAGE_KEY, timeout=5)
                self.location = geocoder.geocode(self.query, language=lang, exactly_one=True)
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                self.location = None
        return super(SearchView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        """Find location by bounding box. Filters also by country,
        because some bbox for some countres are huge (e.g. France, USA).
        """
        qs = Place.objects.none()
        if self.query and self.location:
            country_code = self.location.raw['components'].get('country_code')
            bounds = self.location.raw['bounds']
            lats = (bounds['southwest']['lat'], bounds['northeast']['lat'])
            lngs = (bounds['southwest']['lng'], bounds['northeast']['lng'])
            qs = Place.objects.filter(available=True, deleted=False)
            qs = qs.filter(latitude__range=lats, longitude__range=lngs)
            qs = qs.filter(country=country_code.upper()) if country_code else qs

        """Search in the Profile name and username too."""
        if len(self.query) <= 3:
            return qs
        qs |= Place.objects.filter(owner__user__username__icontains=self.query)
        qs |= Place.objects.filter(owner__first_name__icontains=self.query)
        qs |= Place.objects.filter(owner__last_name__icontains=self.query)
        qs.filter(deleted=False)
        return qs.select_related('owner__user').order_by('country', 'city')

search = SearchView.as_view()


class AuthorizeUserView(LoginRequiredMixin, generic.FormView):
    """Form view to add a user to the list of authorized users
    for a place to be able to see more details."""
    template_name = 'hosting/place_authorized_users.html'
    form_class = AuthorizeUserForm

    def dispatch(self, request, *args, **kwargs):
        self.place = get_object_or_404(Place,
                                       pk=self.kwargs['pk'],
                                       owner=self.request.user.profile)
        return super(AuthorizeUserView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AuthorizeUserView, self).get_context_data(**kwargs)
        context['place'] = self.place
        return context

    def form_valid(self, form):
        user = get_object_or_404(User, username=form.cleaned_data['user'])
        if user not in self.place.authorized_users.all():
            self.place.authorized_users.add(user)
            self.send_email(user, self.place)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('authorize_user', kwargs={'pk': self.kwargs['pk']})

    def send_email(self, user, place):
        subject = _("[Pasporta Servo] You received an Authorization")
        to = [user.email]
        email_template = 'hosting/emails/new_authorization.txt'
        email_context = {
            'user_first_name': user.profile.first_name or user.username,
            'owner_name': place.owner.full_name,
            'place_id': place.pk,
            'site_domain': self.request.get_host(),
            'site_name': settings.SITE_NAME,
        }
        message = render_to_string(email_template, email_context)
        EmailMessage(subject, message, to=to).send()

authorize_user = AuthorizeUserView.as_view()


class AuthorizeUserLinkView(LoginRequiredMixin, generic.View):
    """Add (or remove if present) a user to the list of authorized users
    for a place to be able to see more details."""
    def dispatch(self, request, *args, **kwargs):
        self.user = get_object_or_404(User, username=kwargs['user'])
        self.place = get_object_or_404(Place, pk=kwargs['pk'], owner=request.user.profile)
        if self.user in self.place.authorized_users.all():
            self.place.authorized_users.remove(self.user)
        else:
            self.place.authorized_users.add(self.user)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('authorize_user', kwargs={'pk': self.kwargs['pk']})

authorize_user_link = AuthorizeUserLinkView.as_view()


class FamilyMemberCreateView(LoginRequiredMixin, FamilyMemberMixin, generic.CreateView):
    model = Profile
    form_class = FamilyMemberCreateForm

    def get_form_kwargs(self):
        kwargs = super(FamilyMemberCreateView, self).get_form_kwargs()
        kwargs['place'] = self.place
        return kwargs

family_member_create = FamilyMemberCreateView.as_view()


class FamilyMemberAddMeView(LoginRequiredMixin, FamilyMemberMixin, generic.FormView):
    def post(self, request, *args, **kwargs):
        self.place.family_members.add(request.user.profile)
        return HttpResponseRedirect(self.success_url)

family_member_add_me = FamilyMemberAddMeView.as_view()


class FamilyMemberUpdateView(LoginRequiredMixin, FamilyMemberMixin, generic.UpdateView):
    model = Profile
    form_class = FamilyMemberForm

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


class FamilyMemberDeleteView(LoginRequiredMixin, DeleteMixin, FamilyMemberMixin, generic.DeleteView):
    """Remove the family member for the Place and delete it."""
    model = Profile

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.place.family_members.remove(self.object)
        return super(FamilyMemberDeleteView, self).delete(request, *args, **kwargs)

family_member_delete = FamilyMemberDeleteView.as_view()
