from datetime import datetime
from copy import copy

from markdown2 import markdown
from braces.views import AnonymousRequiredMixin, SuperuserRequiredMixin

from django.views import generic
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.template.response import TemplateResponse
from django.views.decorators.vary import vary_on_headers
from django.conf import settings
from django.contrib import messages
from django.contrib.flatpages.models import FlatPage
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.template.loader import get_template
from django.template import Context
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from blog.models import Post
from hosting.models import Place, Profile
from .auth import AuthMixin, ADMIN, SUPERVISOR, OWNER
from hosting.mixins import ProfileIsUserMixin, ProfileModifyMixin
from .mixins import SupervisorRequiredMixin, UserModifyMixin
from .forms import (
    UsernameUpdateForm, EmailUpdateForm, EmailStaffUpdateForm,
    MassMailForm, UserRegistrationForm
)
from hosting.utils import value_without_invalid_marker, format_lazy
from links.utils import create_unique_url
from .models import SiteConfiguration
from .utils import send_mass_html_mail

config = SiteConfiguration.objects.get()
User = get_user_model()


class HomeView(generic.TemplateView):
    template_name = 'core/home.html'

    def news(self):
        return Post.objects.published(3).defer('content', 'body')

    def right_block(self):
        return FlatPage.objects.filter(url='/home-right-block/').values('content').first()

home = HomeView.as_view()


class RegisterView(AnonymousRequiredMixin, generic.CreateView):
    model = User
    template_name = 'registration/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile_create')

    def get_authenticated_redirect_url(self):
        if self.request.GET.get('next'):
            return self.request.GET['next']
        try:
            # When user is already authenticated, redirect to profile edit page.
            return self.request.user.profile.get_edit_url()
        except Profile.DoesNotExist:
            # If profile does not exist yet, redirect to profile creation page.
            return self.success_url

    def form_valid(self, form):
        self.object = form.save()
        # Keeping this on ice; it interferes with the inline login, probably by wiping the session vars.
        result = super().form_valid(form)
        # Log in user.
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1'])
        login(self.request, user)
        messages.success(self.request, _("You are logged in."))
        return result

register = RegisterView.as_view()


class UsernameChangeView(LoginRequiredMixin, UserModifyMixin, generic.UpdateView):
    model = User
    template_name = 'core/username_change_form.html'
    form_class = UsernameUpdateForm

    def get_object(self, queryset=None):
        self.original_username = self.request.user.username
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Avoid replacement of displayed username via template context when provided value is invalid.
        context['user'].username = self.original_username
        return context

username_change = UsernameChangeView.as_view()


class EmailUpdateView(AuthMixin, UserModifyMixin, generic.UpdateView):
    model = User
    template_name = 'core/system-email_form.html'
    form_class = EmailUpdateForm
    exact_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        print("~  EmailUpdateView#dispatch:1", "[", getattr(self, 'user', None), " / ", self.kwargs.get(self.pk_url_kwarg), "]")
        if not hasattr(self, 'user'):
            self.user = self.request.user
            self.kwargs[self.pk_url_kwarg] = self.user.id
        print("~  EmailUpdateView#dispatch:2", "[", getattr(self, 'user', None), " / ", self.kwargs.get(self.pk_url_kwarg), "]")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        print("~  EmailUpdateView#get_object:1", "[", self.user, "]")
        super().get_object(queryset)
        print("~  EmailUpdateView#get_object:2", "[", self.user, "]")
        return self.user

    def get_owner(self, object):
        return self

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.previous_email != form.instance.email:
            messages.warning(self.request, extra_tags='eminent',
                             message=_("A confirmation email has been sent. "
                                       "Please check your mailbox to complete the process."))
        return response

email_update = EmailUpdateView.as_view()


class EmailVerifyView(LoginRequiredMixin, generic.View):
    """Allows the current user (only) to request a re-verification of their email address."""
    http_method_names = ['post', 'get']
    template_name = 'core/system-email_verify_done.html'

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        email_to_verify = value_without_invalid_marker(request.user.email)
        url = create_unique_url({
            'action': 'email_update',
            'v': True,
            'pk': request.user.pk,
            'email': email_to_verify,
        })
        context = Context({
            'site_name': config.site_name,
            'url': url,
            'user': request.user,
        })
        subject = _("[Pasporta Servo] Is this your email address?")
        email_template_text = get_template('email/system-email_verify.txt')
        email_template_html = get_template('email/system-email_verify.html')
        send_mail(
            subject,
            email_template_text.render(context),
            settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_to_verify],
            html_message=email_template_html.render(context),
            fail_silently=False)

        if request.is_ajax():
            return JsonResponse({'success': 'verification-requested'})
        else:
            return TemplateResponse(request, self.template_name)

    def get(self, request, *args, **kwargs):
        try:
            return HttpResponseRedirect(format_lazy("{settings_url}#{section_email}",
                settings_url=reverse_lazy('profile_settings', kwargs={
                    'pk': request.user.profile.pk, 'slug': slugify(request.user.username)}),
                section_email=_("email-addr"))
            )
        except Profile.DoesNotExist:
            return HttpResponseRedirect(reverse_lazy('email_update'))

email_verify = EmailVerifyView.as_view()


class EmailUpdateConfirmView(LoginRequiredMixin, generic.View):
    """
    Confirms for the current user (only) the email address in the request as valid
    and updates it in the database.
    This is an internal view not accessible via a URL.
    """

    def dispatch(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['pk'])
        if user.pk != request.user.pk:
            raise Http404("Only user the token was created for can use this view.")
        old_email, new_email = user.email, kwargs['email']
        user.email = new_email
        user.save()
        if 'verification' in kwargs and kwargs['verification']:
            messages.info(request, _("Your email address has been successfully verified!"), extra_tags='eminent')
        else:
            messages.info(request, _("Your email address has been successfully updated!"), extra_tags='eminent')
        try:
            if user.profile.email == old_email:  # Keep profile email in sync
                user.profile.email = new_email
                user.profile.save()
            return HttpResponseRedirect(reverse_lazy('profile_settings', kwargs={
                'pk': user.profile.pk, 'slug': slugify(user.username)}))
        except Profile.DoesNotExist:
            return HttpResponseRedirect(reverse_lazy('profile_create'))

email_update_confirm = EmailUpdateConfirmView.as_view()


class EmailStaffUpdateView(AuthMixin, ProfileIsUserMixin, ProfileModifyMixin, generic.UpdateView):
    model = Profile
    template_name = 'core/system-email_form.html'
    form_class = EmailStaffUpdateForm
    minimum_role = SUPERVISOR

    def get_object(self, queryset=None):
        self.user = super().get_object(queryset).user
        return self.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # We want the displayed logged in user still be request.user and not the modified User instance.
        context['user'] = self.request.user
        return context

staff_email_update = EmailStaffUpdateView.as_view()


class EmailValidityMarkView(AuthMixin, ProfileIsUserMixin, generic.View):
    http_method_names = ['post']
    template_name = '404.html'
    minimum_role = SUPERVISOR
    valid = False

    def dispatch(self, request, *args, **kwargs):
        self.profile = get_object_or_404(Profile, pk=kwargs['pk'])
        kwargs['auth_base'] = self.profile
        return super().dispatch(request, *args, **kwargs)

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        if self.valid:
            Profile.mark_valid_emails([self.profile.user.email])
        else:
            Profile.mark_invalid_emails([self.profile.user.email])
        if request.is_ajax():
            success_value = 'valid' if self.valid else 'invalid'
            return JsonResponse({'success': success_value})
        else:
            return TemplateResponse(request, self.template_name, context={'view': self})

email_mark_invalid = EmailValidityMarkView.as_view()
email_mark_valid = EmailValidityMarkView.as_view(valid=True)


class MassMailView(AuthMixin, generic.FormView):
    template_name = 'core/mass_mail_form.html'
    form_class = MassMailForm
    display_permission_denied = False
    exact_role = ADMIN

    def dispatch(self, request, *args, **kwargs):
        kwargs['auth_base'] = None
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return format_lazy("{success_url}?nb={sent}",
            success_url=reverse_lazy('mass_mail_sent'), sent=self.nb_sent)

    def form_valid(self, form):
        body = form.cleaned_data['body']
        md_body = markdown(body)
        subject = form.cleaned_data['subject']
        preheader = form.cleaned_data['preheader']
        heading = form.cleaned_data['heading']
        category = form.cleaned_data['categories']
        default_from = settings.DEFAULT_FROM_EMAIL
        template = get_template('email/mass_email.html')

        opening = datetime(2014, 11, 24)
        places = Place.objects.select_related('owner__user')
        profiles = []

        if category in ("test", "just_user"):
            places = []
            # only active profiles, linked to existing user accounts
            profiles = Profile.objects.filter(user__isnull=False)
            # exclude completely those who have at least one active available place
            profiles = profiles.exclude(owned_places=Place.objects.filter(available=True))
            # remove profiles with places available in the past, that is deleted
            profiles = profiles.filter(Q(owned_places__available=False) | Q(owned_places__isnull=True))
            # finally remove duplicates
            profiles = profiles.distinct()
        elif category == "old_system":
            # those who logged in before the opening date; essentially, never used the new system
            profiles = Profile.objects.filter(user__last_login__lte=opening).distinct()
        else:
            # those who logged in after the opening date
            profiles = Profile.objects.filter(user__last_login__gt=opening)
            # filter by active places according to 'in-book?' selection
            if category == "in_book":
                profiles = profiles.filter(owned_places__in_book=True)
            elif category == "not_in_book":
                profiles = profiles.filter(owned_places__in_book=False, owned_places__available=True)
            # finally remove duplicates
            profiles = profiles.distinct()

        if category == 'test':
            test_email = form.cleaned_data['test_email']
            context = Context({
                'preheader': preheader,
                'heading': heading,
                'body': mark_safe(md_body.format(nomo=test_email)),
            })
            messages = [(
                subject,
                body.format(nomo=test_email),
                template.render(context),
                default_from,
                [test_email]
            )]

        else:
            context = Context({
                'preheader': preheader,
                'heading': heading,
            })
            messages = [(
                subject,
                body.format(nomo=profile.name),
                template.render(copy(context).update(
                    {'body': mark_safe(md_body.format(nomo=escape(profile.name)))}
                )),
                default_from,
                [value_without_invalid_marker(profile.user.email)]
            ) for profile in profiles] if profiles else []

        self.nb_sent = send_mass_html_mail(messages)
        return super().form_valid(form)

mass_mail = MassMailView.as_view()


class MassMailSentView(AuthMixin, generic.TemplateView):
    template_name = 'core/mass_mail_sent.html'
    display_permission_denied = False
    exact_role = ADMIN

    def dispatch(self, request, *args, **kwargs):
        kwargs['auth_base'] = None
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nb'] = int(self.request.GET['nb']) if self.request.GET.get('nb', '').isdigit() else '??'
        return context

mass_mail_sent = MassMailSentView.as_view()
