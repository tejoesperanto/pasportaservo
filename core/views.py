from copy import copy
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.views import (
    LoginView as LoginBuiltinView,
    PasswordChangeDoneView as PasswordChangeDoneBuiltinView,
    PasswordChangeView as PasswordChangeBuiltinView,
)
from django.contrib.flatpages.models import FlatPage
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import (
    Http404, HttpResponse, HttpResponseRedirect, JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from django.views import generic
from django.views.decorators.vary import vary_on_headers

from commonmark import commonmark

from blog.models import Post
from core.models import Policy
from hosting.models import Phone, Place, Profile
from hosting.utils import value_without_invalid_marker
from hosting.views.mixins import (
    ProfileIsUserMixin, ProfileMixin, ProfileModifyMixin,
)
from links.utils import create_unique_url

from .auth import ADMIN, OWNER, SUPERVISOR, AuthMixin
from .forms import (
    EmailStaffUpdateForm, EmailUpdateForm, MassMailForm,
    UsernameUpdateForm, UserRegistrationForm,
)
from .mixins import LoginRequiredMixin, UserModifyMixin, flatpages_as_templates
from .models import Agreement, SiteConfiguration
from .utils import sanitize_next, send_mass_html_mail

User = get_user_model()


@flatpages_as_templates
class HomeView(generic.TemplateView):
    template_name = 'core/home.html'

    @cached_property
    def news(self):
        return Post.objects.published().defer('content', 'body')[:3]

    @cached_property
    def right_block(self):
        block = FlatPage.objects.filter(url='/home-right-block/').values('content').first()
        return self.render_flat_page(block)


class LoginView(LoginBuiltinView):
    # This view enables support for both a custom URL parameter name
    # for redirection, as well as the built-in one (`next`). This is
    # needed for third-party libraries that use Django's functions
    # such as the `login_required` decorator, and cannot be customised.
    redirect_authenticated_user = True
    redirect_field_name = settings.REDIRECT_FIELD_NAME

    def get_redirect_url(self):
        if 'next' in self.request.POST and self.redirect_field_name not in self.request.POST:
            self.request.POST = self.request.POST.copy()
            self.request.POST[self.redirect_field_name] = self.request.POST['next']
        if 'next' in self.request.GET and self.redirect_field_name not in self.request.GET:
            self.request.GET = self.request.GET.copy()
            self.request.GET[self.redirect_field_name] = self.request.GET['next']

        return super().get_redirect_url()


class RegisterView(generic.CreateView):
    model = User
    template_name = 'registration/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile_create')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Only anonymous (non-authenticated) users should access the registration page.
            return HttpResponseRedirect(self.get_authenticated_redirect_url())
        return super().dispatch(request, *args, **kwargs)

    def get_authenticated_redirect_url(self):
        redirect_to = sanitize_next(self.request)
        if redirect_to:
            return redirect_to
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


@flatpages_as_templates
class AgreementView(LoginRequiredMixin, generic.TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'core/consent.html'
    standalone_policy_view = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['consent_required'] = getattr(self.request.user, 'consent_required', [None])[0]
        context['effective_date'], __ = self._agreement
        return context

    @cached_property
    def _agreement(self):
        policy = (
            getattr(self.request.user, 'consent_required', None)
            or getattr(self.request.user, 'consent_obtained', None)
        )[0]  # Fetch the policy from the lazy collection.
        effective_date = Policy.get_effective_date_for_policy(policy['content'])
        return (effective_date, policy)

    @cached_property
    def agreement(self):
        __, policy = self._agreement
        return self.render_flat_page(policy)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'unknown')
        if action == 'approve':
            if getattr(request.user, 'consent_required', False):
                Agreement.objects.create(
                    user=request.user,
                    policy_version=request.user.consent_required[0]['version'])
            target_page = sanitize_next(request)
            return HttpResponseRedirect(target_page or reverse_lazy('home'))
        elif action == 'reject':
            request.session['agreement_rejected'] = self._agreement[1]['version']
            return HttpResponseRedirect(reverse_lazy('agreement_reject'))
        else:
            return HttpResponseRedirect(reverse_lazy('agreement'))


class AgreementRejectView(LoginRequiredMixin, generic.TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'core/consent_rejected.html'

    def get(self, request, *args, **kwargs):
        """
        Show the warning about consequences of not accepting the agreement.
        """
        agreement = request.session.pop('agreement_rejected', None)
        if not agreement:
            return HttpResponse()
        request.session['agreement_rejected_final'] = agreement
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Set the flag 'deleted' to True on the user's profile,
        set the flag 'deleted' to True on all associated objects,
        deactivate the user account,
        and then redirect to home URL.
        """
        agreement = request.session.pop('agreement_rejected_final', None)
        if not agreement:
            return HttpResponse()
        now = timezone.now()
        owned_places = Place.all_objects.filter(owner__user=request.user)
        owned_phones = Phone.all_objects.filter(profile__user=request.user)
        with transaction.atomic():
            [qs.update(deleted_on=now) for qs in [
                # Family members who are not users by themselves.
                Profile.objects.filter(
                    pk__in=owned_places.values_list('family_members', flat=True),
                    deleted=False, user_id__isnull=True),
                # Places which were not previously deleted.
                owned_places.filter(deleted=False),
                # Phones which were not previously deleted.
                owned_phones.filter(deleted=False),
                # The profile itself.
                Profile.objects.filter(user=request.user),
            ]]
            request.user.is_active = False
            request.user.save(update_fields=['is_active'])
            agreement = Agreement.objects.filter(
                user=request.user, policy_version=agreement, withdrawn__isnull=True)
            agreement.update(withdrawn=now)
        messages.info(request, _("Farewell !"))
        return HttpResponseRedirect(reverse_lazy('home'))


class PasswordChangeView(LoginRequiredMixin, PasswordChangeBuiltinView):
    # Must use the custom LoginRequired mixin, otherwise redirection
    # after the authentication will not work as expected.
    pass


class PasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneBuiltinView):
    # Must use the custom LoginRequired mixin, otherwise redirection
    # after the authentication will not work as expected.
    pass


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


class EmailUpdateView(AuthMixin, UserModifyMixin, generic.UpdateView):
    model = User
    template_name = 'core/system-email_form.html'
    form_class = EmailUpdateForm
    exact_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(self, 'user'):
            self.user = self.request.user
            self.kwargs[self.pk_url_kwarg] = self.user.pk
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        super().get_object(queryset)
        return self.user

    def get_owner(self, object):
        try:
            return self.user.profile
        except Profile.DoesNotExist:
            # For users without a profile, we must create a dummy one, because AuthMixin
            # expects all owners to be instances of Profile (which is not unreasonable).
            return Profile(user=copy(self.user))

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.previous_email != form.instance.email:
            messages.warning(self.request, extra_tags='eminent',
                             message=_("A confirmation email has been sent. "
                                       "Please check your mailbox to complete the process."))
        return response


class EmailVerifyView(LoginRequiredMixin, generic.View):
    """
    Allows the current user (only) to request a re-verification of their email
    address.
    """
    http_method_names = ['post', 'get']
    template_name = 'core/system-email_verify_done.html'

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        config = SiteConfiguration.get_solo()
        email_to_verify = value_without_invalid_marker(request.user.email)
        url = create_unique_url({
            'action': 'email_update',
            'v': True,
            'pk': request.user.pk,
            'email': email_to_verify,
        })
        context = {
            'site_name': config.site_name,
            'url': url,
            'user': request.user,
        }
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
            return HttpResponseRedirect(format_lazy(
                "{settings_url}#{section_email}",
                settings_url=reverse_lazy('profile_settings', kwargs={
                    'pk': request.user.profile.pk, 'slug': request.user.profile.autoslug}),
                section_email=pgettext_lazy("URL", "email-addr"),
            ))
        except Profile.DoesNotExist:
            return HttpResponseRedirect(reverse_lazy('email_update'))


class EmailUpdateConfirmView(LoginRequiredMixin, generic.View):
    """
    Confirms for the current user (only) the email address in the request as
    valid and updates it in the database.
    This is an internal view not accessible via a URL.
    The check that the user is authenticated is performed in the dispatch()
    method of the mixin.
    """

    def get(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['pk'])
        if user.pk != request.user.pk:
            raise Http404("Only user the token was created for can use this view.")
        old_email, new_email = user.email, kwargs['email']
        user.email = new_email
        user.save()
        if kwargs.get('verification'):
            messages.info(request, _("Your email address has been successfully verified!"), extra_tags='eminent')
        else:
            messages.info(request, _("Your email address has been successfully updated!"), extra_tags='eminent')
        try:
            if user.profile.email == old_email:  # Keep profile email in sync
                user.profile.email = new_email
                user.profile.save()
        except Profile.DoesNotExist:
            return HttpResponseRedirect(reverse_lazy('profile_create'))
        else:
            return HttpResponseRedirect(reverse_lazy('profile_settings', kwargs={
                'pk': user.profile.pk, 'slug': user.profile.autoslug}))


class EmailStaffUpdateView(AuthMixin, ProfileIsUserMixin, ProfileMixin, ProfileModifyMixin, generic.UpdateView):
    """
    Allows supervisors to modify the email address for a user account.
    """
    template_name = 'core/system-email_form.html'
    form_class = EmailStaffUpdateForm
    minimum_role = SUPERVISOR

    def get_queryset(self):
        return super().get_queryset().select_related('user')

    def get_object(self, queryset=None):
        self.user = super().get_object(queryset).user
        return self.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # We want the displayed logged in user still be request.user and not the modified User instance.
        context['user'] = self.request.user
        return context


class EmailValidityMarkView(AuthMixin, ProfileIsUserMixin, ProfileMixin, generic.View):
    http_method_names = ['post']
    template_name = '200.html'
    minimum_role = SUPERVISOR
    valid = False

    def dispatch(self, request, *args, **kwargs):
        self.profile = self.get_object()
        kwargs['auth_base'] = self.profile
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().select_related(None)

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        # Spare the extra trip to the database to fetch the User object associated
        # with the profile, just to retrieve the email address in that record.
        email = User.objects.filter(pk=self.profile.user_id).values_list('email')
        if self.valid:
            Profile.mark_valid_emails(email)
        else:
            Profile.mark_invalid_emails(email)
        if request.is_ajax():
            success_value = 'valid' if self.valid else 'invalid'
            return JsonResponse({'success': success_value})
        else:
            return TemplateResponse(request, self.template_name, context={'view': self})


class MassMailView(AuthMixin, generic.FormView):
    template_name = 'core/mass_mail_form.html'
    form_class = MassMailForm
    display_permission_denied = False
    exact_role = ADMIN

    def dispatch(self, request, *args, **kwargs):
        kwargs['auth_base'] = None
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return format_lazy(
            "{success_url}?nb={sent}",
            success_url=reverse_lazy('mass_mail_sent'),
            sent=self.nb_sent,
        )

    def form_valid(self, form):
        body = form.cleaned_data['body']
        md_body = commonmark(body)
        subject = form.cleaned_data['subject']
        preheader = form.cleaned_data['preheader']
        heading = form.cleaned_data['heading']
        category = form.cleaned_data['categories']
        default_from = settings.DEFAULT_FROM_EMAIL
        template = get_template('email/mass_email.html')

        opening = datetime(2014, 11, 24)
        profiles = []

        if category in ("test", "just_user"):
            # only active profiles, linked to existing user accounts
            profiles = Profile.objects.filter(user__isnull=False)
            # exclude completely those who have at least one active available place
            profiles = profiles.exclude(owned_places__in=Place.objects.filter(available=True))
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
            context = {
                'preheader': mark_safe(preheader.format(nomo=test_email)),
                'heading': heading,
                'body': mark_safe(md_body.format(nomo=test_email)),
            }
            messages = [(
                subject,
                body.format(nomo=test_email),
                template.render(context),
                default_from,
                [test_email]
            )]

        else:
            name_placeholder = _("user")
            messages = [(
                subject,
                body.format(nomo=profile.name or name_placeholder),
                template.render({
                    'preheader': mark_safe(preheader.format(nomo=escape(profile.name or name_placeholder))),
                    'heading': heading,
                    'body': mark_safe(md_body.format(nomo=escape(profile.name or name_placeholder))),
                }),
                default_from,
                [value_without_invalid_marker(profile.user.email)]
            ) for profile in profiles] if profiles else []

        self.nb_sent = send_mass_html_mail(messages)
        return super().form_valid(form)


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
