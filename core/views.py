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
from hosting.mixins import SupervisorRequiredMixin, ProfileMixin
from .forms import (
    UsernameUpdateForm, EmailUpdateForm, StaffUpdateEmailForm,
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
            return reverse_lazy('profile_create')

    def form_valid(self, form):
        self.object = form.save()
        # Keeping this on ice; it interferes with the inline login, probably by wiping the session vars.
        result = super(RegisterView, self).form_valid(form)
        # Log in user.
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1'])
        login(self.request, user)
        messages.success(self.request, _("You are logged in."))
        return result

register = RegisterView.as_view()


class UsernameChangeView(LoginRequiredMixin, generic.UpdateView):
    model = User
    template_name = 'core/username_change_form.html'
    form_class = UsernameUpdateForm

    def get_object(self, queryset=None):
        self.original_username = self.request.user.username
        return self.request.user

    def get_success_url(self, *args, **kwargs):
        try:
            return self.object.profile.get_edit_url()
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # avoid replacement of displayed username via template context when provided value is invalid
        context['user'].username = self.original_username
        return context

username_change = UsernameChangeView.as_view()


class EmailUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = User
    template_name = 'core/system-email_form.html'
    form_class = EmailUpdateForm

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self, *args, **kwargs):
        try:
            return self.object.profile.get_edit_url()
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')

    def form_valid(self, form):
        response = super(EmailUpdateView, self).form_valid(form)
        if form.previous_email != form.instance.email:
            messages.warning(self.request, extra_tags='eminent',
                             message=_("A confirmation email has been sent. "
                                       "Please check your mailbox to complete the process."))
        return response

email_update = EmailUpdateView.as_view()


class EmailVerifyView(LoginRequiredMixin, generic.View):
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


class StaffUpdateEmailView(LoginRequiredMixin, SupervisorRequiredMixin, ProfileMixin, generic.UpdateView):
    model = User
    form_class = StaffUpdateEmailForm
    template_name = 'core/system-email_form.html'
    staff_view = True

    def dispatch(self, request, *args, **kwargs):
        self.user = get_object_or_404(Profile, pk=kwargs['pk']).user
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.user

    def get_context_data(self, **kwargs):
        context = super(StaffUpdateEmailView, self).get_context_data(**kwargs)
        # we want the displayed logged in user still be request.user and not the modified User instance
        context['user'] = self.request.user
        return context

staff_update_email = StaffUpdateEmailView.as_view()


class MarkEmailValidityView(LoginRequiredMixin, SupervisorRequiredMixin, generic.View):
    http_method_names = ['post']
    template_name = '404.html'
    valid = False

    def dispatch(self, request, *args, **kwargs):
        self.user = get_object_or_404(Profile, pk=kwargs['pk']).user
        return super().dispatch(request, *args, **kwargs)

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        if self.valid:
            Profile.mark_valid_emails([self.user.email])
        else:
            Profile.mark_invalid_emails([self.user.email])
        if request.is_ajax():
            success_value = 'valid' if self.valid else 'invalid'
            return JsonResponse({'success': success_value})
        else:
            return TemplateResponse(request, self.template_name)

mark_email_invalid = MarkEmailValidityView.as_view()
mark_email_valid = MarkEmailValidityView.as_view(valid=True)


class MassMailView(SuperuserRequiredMixin, generic.FormView):
    template_name = 'core/mass_mail_form.html'
    form_class = MassMailForm

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
        return super(MassMailView, self).form_valid(form)

mass_mail = MassMailView.as_view()


class MassMailSentView(SuperuserRequiredMixin, generic.TemplateView):
    template_name = 'core/mass_mail_sent.html'

    def get_context_data(self, **kwargs):
        context = super(MassMailSentView, self).get_context_data(**kwargs)
        context['nb'] = int(self.request.GET['nb']) if self.request.GET.get('nb', '').isdigit() else '??'
        return context

mass_mail_sent = MassMailSentView.as_view()
