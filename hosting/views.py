from django.views import generic
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.utils.translation import ugettext_lazy as _

from braces.views import AnonymousRequiredMixin, LoginRequiredMixin

from .models import Profile, Place, Phone, Condition
from .forms import UserRegistrationForm, ProfileForm


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
