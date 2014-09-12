import geopy

from django.views import generic
from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.utils.translation import ugettext_lazy as _

from braces.views import AnonymousRequiredMixin, LoginRequiredMixin

from .models import Profile, Place, Phone, Condition
from .forms import UserRegistrationForm, ProfileForm

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
        # Log user in
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1'])
        login(self.request, user)
        messages.success(self.request, "You are logged in.")
        return super(RegisterView, self).form_valid(form)

register = RegisterView.as_view()


class ProfileCreateView(LoginRequiredMixin, generic.CreateView):
    model = Profile
    form_class = ProfileForm
    success_url = reverse_lazy('profile_detail')

    def get_form(self, form_class):
        user = self.request.user
        return form_class(user=user, **self.get_form_kwargs())

profile_create = ProfileCreateView.as_view()


class ProfileDetailView(LoginRequiredMixin, generic.DetailView):
    model = Profile

    def get_object(self, queryset=None):
        return self.request.user.profile

profile_detail = ProfileDetailView.as_view()


class SearchView(generic.ListView):
    model = Place

    def get(self, request, *args, **kwargs):
        self.query = request.GET.get('q')
        if self.query:
            try:
                geocoder = geopy.geocoders.Nominatim(timeout=5)
                self.location = geocoder.geocode(self.query, language=lang,
                        exactly_one=True, addressdetails=True)
            except geopy.exc.GeocoderTimedOut:
                self.location = None
                self.timedout = True
        return super(SearchView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        if not self.query or not self.location:
            return Place.objects.none()
        bbox = self.location.raw['boundingbox']
        lats, lngs = bbox[:2], bbox[2:]
        qs = Place.objects.filter(available=True)
        return qs.filter(latitude__range=lats, longitude__range=lngs)

    def get_context_data(self, **kwargs):
        context = super(SearchView, self).get_context_data(**kwargs)
        context['query'] = self.query
        if self.query:
            context['location'] = getattr(self.location, 'raw', '')
            context['timedout'] = getattr(self, 'timedout', False)
        return context

search = SearchView.as_view()
