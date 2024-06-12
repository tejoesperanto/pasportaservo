import logging
import re
from copy import copy
from datetime import datetime, timedelta
from traceback import format_exception
from typing import cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.views import (
    LoginView as LoginBuiltinView, LogoutView as LogoutBuiltinView,
    PasswordChangeDoneView as PasswordChangeDoneBuiltinView,
    PasswordChangeView as PasswordChangeBuiltinView,
    PasswordResetConfirmView as PasswordResetConfirmBuiltinView,
    PasswordResetView as PasswordResetBuiltinView,
)
from django.contrib.flatpages.models import FlatPage
from django.core.mail import mail_admins, send_mail
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.http import (
    Http404, HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict,
)
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import (
    SimpleLazyObject, cached_property, classproperty,
)
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import format_lazy
from django.utils.timezone import make_aware
from django.utils.translation import (
    get_language, gettext, gettext_lazy as _, pgettext, pgettext_lazy,
)
from django.views import generic
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.vary import vary_on_headers

from commonmark import commonmark
from gql import Client as GQLClient, gql
from gql.transport.exceptions import TransportError, TransportQueryError
from gql.transport.requests import RequestsHTTPTransport as GQLHttpTransport
from graphql import GraphQLError

from blog.models import Post
from core.models import Policy
from hosting.forms import SubregionForm
from hosting.models import Phone, Place, Profile
from hosting.utils import value_without_invalid_marker
from hosting.views.mixins import (
    ProfileIsUserMixin, ProfileMixin, ProfileModifyMixin,
)
from links.utils import create_unique_url
from shop.models import Reservation

from .auth import AuthMixin, AuthRole
from .forms import (
    EmailStaffUpdateForm, EmailUpdateForm, FeedbackForm, MassMailForm,
    SystemPasswordChangeForm, UserAuthenticationForm,
    UsernameRemindRequestForm, UsernameUpdateForm, UserRegistrationForm,
)
from .mixins import (
    FlatpageAsTemplateMixin, LoginRequiredMixin,
    UserModifyMixin, flatpages_as_templates,
)
from .models import FEEDBACK_TYPES, Agreement, SiteConfiguration
from .utils import sanitize_next, send_mass_html_mail

User = get_user_model()


@flatpages_as_templates
class HomeView(FlatpageAsTemplateMixin, generic.TemplateView):
    template_name = 'core/home.html'

    @cached_property
    def news(self):
        return Post.objects.published().defer('content', 'body')[:3]

    @cached_property
    def right_block(self):
        block = FlatPage.objects.filter(url='/home-right-block/').values('content').first()
        return self.render_flat_page(cast(FlatpageAsTemplateMixin.DictWithContent, block))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            @SimpleLazyObject
            def donations_count():
                return sum(
                    Reservation.objects
                    .filter(user=self.request.user, product__code='Donation')
                    .values_list('amount', flat=True)
                )
            context['user_donations_count'] = donations_count
        return context


class LoginView(LoginBuiltinView):
    """
    This view enables support for both a custom URL parameter name
    for redirection, as well as the built-in one (`next`). This is
    needed for third-party libraries that use Django's functions
    such as the `login_required` decorator, and cannot be customised.
    """
    authentication_form = UserAuthenticationForm
    redirect_authenticated_user = True
    redirect_field_name = settings.REDIRECT_FIELD_NAME

    def get_redirect_url(self):
        if 'next' in self.request.POST and self.redirect_field_name not in self.request.POST:
            self.request.POST = self.request.POST.copy()
            self.request.POST[self.redirect_field_name] = self.request.POST['next']
        if 'next' in self.request.GET and self.redirect_field_name not in self.request.GET:
            self.request.GET = self.request.GET.copy()
            self.request.GET[self.redirect_field_name] = self.request.GET['next']

        redirect_to = super().get_redirect_url()
        if redirect_to == self.request.path:
            return ''  # Avoid a redirection loop.
        else:
            return redirect_to

    def render_to_response(self, context, **response_kwargs) -> HttpResponse:
        # The view is rendered, which means that the user is not logged in.
        response = super().render_to_response(context, **response_kwargs)
        response.delete_cookie(
            'seen_at',
            domain=settings.SESSION_COOKIE_DOMAIN, path=settings.SESSION_COOKIE_PATH,
        )
        return response

    def form_valid(self, form) -> HttpResponse:
        # User successfully logged in.
        response = super().form_valid(form)
        response.set_cookie(
            'seen_at', str(int(datetime.now().timestamp())),
            max_age=(
                settings.SESSION_COOKIE_AGE
                if not settings.SESSION_EXPIRE_AT_BROWSER_CLOSE
                else None
            ),
            domain=settings.SESSION_COOKIE_DOMAIN, path=settings.SESSION_COOKIE_PATH,
            secure=settings.SESSION_COOKIE_SECURE, httponly=True, samesite='Lax',
        )
        return response


class LogoutView(LogoutBuiltinView):
    redirect_field_name = settings.REDIRECT_FIELD_NAME

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response.delete_cookie(
            'seen_at',
            domain=settings.SESSION_COOKIE_DOMAIN, path=settings.SESSION_COOKIE_PATH,
        )
        return response


class RegisterView(generic.CreateView):
    model = User
    template_name = 'registration/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile_create')

    @method_decorator(sensitive_post_parameters('password1', 'password2'))
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
            profile = Profile.get_basic_data(user=self.request.user)
            return profile.get_edit_url()
        except Profile.DoesNotExist:
            # If profile does not exist yet, redirect to profile creation page.
            return self.success_url

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['view_request'] = self.request
        return kwargs

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


class AccountRestoreRequestView(generic.TemplateView):
    template_name = '200.html'

    @never_cache
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Only anonymous (non-authenticated) users are expected to access this page.
            return HttpResponseRedirect(self.get_authenticated_redirect_url())
        request_id = request.session.pop('restore_request_id', None)
        if request_id is None or not isinstance(request_id[1], float):
            # When the restore request ID is missing or invalid, just show the login page.
            return HttpResponseRedirect(reverse_lazy('login'))
        if datetime.now() - datetime.fromtimestamp(request_id[1]) > timedelta(hours=1):
            # When the restore request ID is expired (older than 1 hour), redirect to the login page.
            # This is to prevent abuse, when the user leaves their browser or device open and
            # a different person attempts to (mis)use the restoration request functionality...
            messages.warning(self.request, _("Something misfunctioned. Please log in again and retry."))
            return HttpResponseRedirect(reverse_lazy('login'))
        # Otherwise, send mail to admins.
        send_mail(
            '{prefix}{subject}'.format(
                prefix=settings.EMAIL_SUBJECT_PREFIX,
                subject=gettext(
                    # xgettext:python-brace-format
                    "Note to admin: User requests to reactivate their account; ref: {}."
                ).format(request_id[0])),
            "--",
            None,
            ['{} <{}>'.format(nick, addr) for nick, addr in settings.ADMINS],
            fail_silently=False)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_authenticated_redirect_url(self):
        redirect_to = sanitize_next(self.request)
        if redirect_to:
            return redirect_to
        try:
            # When user is already authenticated, redirect to profile's page.
            profile = Profile.get_basic_data(user=self.request.user)
            return profile.get_absolute_url()
        except Profile.DoesNotExist:
            # If profile does not exist yet, redirect to home.
            return reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['success_message'] = _("An administrator will contact you soon.")
        return context


@flatpages_as_templates
class AgreementView(LoginRequiredMixin, FlatpageAsTemplateMixin, generic.TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'account/consent.html'
    standalone_policy_view = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['consent_required'] = getattr(self.request.user, 'consent_required', False)
        context['consent_obtained'] = getattr(self.request.user, 'consent_obtained', False)
        context['effective_date'] = self._agreement.effective_date
        return context

    @cached_property
    def _agreement(self) -> Policy:
        policy_source = (
            getattr(self.request.user, 'consent_required', {})
            or getattr(self.request.user, 'consent_obtained', {})
        ).get('current', [])
        policy = list(policy_source)[0]  # Fetch the policy from the lazy collection.
        return policy

    @cached_property
    def agreement(self) -> str:
        return self.render_flat_page(self._agreement)

    @cached_property
    def terms(self) -> list[str]:
        tcpage = FlatPage.objects.filter(url='/terms-conditions/').values('content').first()
        terms = self.render_flat_page(cast(FlatpageAsTemplateMixin.DictWithContent, tcpage))
        terms = terms.rstrip()
        if not terms:
            return []
        return re.split(r'\r?\n\r?\n', terms.lstrip('\n\r'))

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'unknown')
        if action == 'approve':
            if hasattr(request.user, 'consent_required'):
                Agreement.objects.create(
                    user=request.user,
                    policy_version=request.user.consent_required['current'][0].version)
            target_page = sanitize_next(request)
            return HttpResponseRedirect(target_page or reverse_lazy('home'))
        elif action == 'reject':
            request.session['agreement_rejected'] = self._agreement.version
            return HttpResponseRedirect(reverse_lazy('agreement_reject'))
        else:
            return HttpResponseRedirect(reverse_lazy('agreement'))


class AgreementRejectView(LoginRequiredMixin, generic.TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'account/consent_rejected.html'

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
        logout(request)
        messages.info(request, _("Farewell !"))
        return HttpResponseRedirect(reverse_lazy('home'))


class AccountSettingsView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'account/settings.html'
    display_fair_usage_condition = True

    def get(self, request, *args, **kwargs):
        try:
            profile = Profile.get_basic_data(request, user=request.user)
            return HttpResponseRedirect(
                reverse_lazy('profile_settings', kwargs={'pk': profile.pk, 'slug': profile.autoslug})
            )
        except Profile.DoesNotExist:
            # Cache the result for the reverse related descriptor, to spare further DB queries.
            setattr(request.user, request.user._meta.get_field('profile').get_cache_name(), None)
            return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['account'] = self.request.user
        return context


class PasswordResetView(PasswordResetBuiltinView):
    """
    This extension of Django's built-in view allows to send a different
    email depending on whether the user is active (True) or no (False).
    See also the companion `SystemPasswordResetRequestForm`.
    """
    html_email_template_name = {True: 'email/password_reset.html', False: 'email/password_reset_activate.html'}
    email_template_name = {True: 'email/password_reset.txt', False: 'email/password_reset_activate.txt'}
    subject_template_name = 'email/password_reset_subject.txt'


class PasswordResetConfirmView(PasswordResetConfirmBuiltinView):
    @classproperty
    def reset_url_token(self):
        return pgettext("URL", "set-password")


class PasswordChangeView(LoginRequiredMixin, PasswordChangeBuiltinView):
    # Must use the custom LoginRequired mixin, otherwise redirection
    # after the authentication will not work as expected.
    template_name = 'account/password_change_form.html'
    form_class = SystemPasswordChangeForm


class PasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneBuiltinView):
    # Must use the custom LoginRequired mixin, otherwise redirection
    # after the authentication will not work as expected.
    template_name = 'account/password_change_done.html'


class UsernameRemindView(PasswordResetView):
    template_name = 'registration/username_remind_form.html'
    form_class = UsernameRemindRequestForm
    html_email_template_name = {True: 'email/username_remind.html', False: 'email/username_remind_activate.html'}
    email_template_name = {True: 'email/username_remind.txt', False: 'email/username_remind_activate.txt'}
    subject_template_name = 'email/username_remind_subject.txt'
    success_url = reverse_lazy('username_remind_done')


class UsernameRemindDoneView(generic.TemplateView):
    template_name = 'registration/username_remind_done.html'


class UsernameChangeView(LoginRequiredMixin, UserModifyMixin, generic.UpdateView):
    model = User
    template_name = 'account/username_change_form.html'
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
    template_name = 'account/system-email_form.html'
    form_class = EmailUpdateForm
    exact_role = AuthRole.OWNER

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
            if self.request.user_has_profile:
                return self.user.profile
            else:
                raise Profile.DoesNotExist
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
    template_name = 'account/system-email_verify_done.html'

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        config = SiteConfiguration.get_solo()
        email_to_verify = value_without_invalid_marker(request.user.email)
        url, token = create_unique_url({
            'action': 'email_update',
            'v': True,
            'pk': request.user.pk,
            'email': email_to_verify,
        })
        context = {
            'site_name': config.site_name,
            'ENV': settings.ENVIRONMENT,
            'RICH_ENVELOPE': getattr(settings, 'EMAIL_RICH_ENVELOPES', None),
            'subject_prefix': settings.EMAIL_SUBJECT_PREFIX_FULL,
            'url': url,
            'url_first': url[:url.rindex('/')+1],
            'url_second': token,
            'user': request.user,
        }
        email_template_subject = get_template('email/system-email_verify_subject.txt')
        email_template_text = get_template('email/system-email_verify.txt')
        email_template_html = get_template('email/system-email_verify.html')
        send_mail(
            ''.join(email_template_subject.render(context).splitlines()),  # no newlines allowed in subject.
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
            profile = Profile.get_basic_data(user=request.user)
            settings_url = reverse_lazy('profile_settings', kwargs={
                'pk': profile.pk, 'slug': profile.autoslug})
        except Profile.DoesNotExist:
            settings_url = reverse_lazy('account_settings')

        return HttpResponseRedirect(format_lazy(
            '{settings_url}#{section_email}',
            settings_url=settings_url,
            section_email=pgettext_lazy("URL", "email-addr"),
        ))


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
    template_name = 'account/system-email_form.html'
    form_class = EmailStaffUpdateForm
    minimum_role = AuthRole.SUPERVISOR

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
    minimum_role = AuthRole.SUPERVISOR
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


class AccountDeleteView(LoginRequiredMixin, generic.DeleteView):
    """
    Allows the current user (only) to delete -- that is, disable -- their
    account.  When the user has a profile, they will be redirected to the
    more feature-rich ProfileDeleteView.
    """
    model = User
    template_name = 'account/account_confirm_delete.html'
    success_url = reverse_lazy('logout')

    def get_object(self, queryset=None):
        return self.request.user

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_active:
            return HttpResponseRedirect(self.get_success_url())
        else:
            try:
                profile = Profile.get_basic_data(user=request.user)
            except Profile.DoesNotExist:
                return super().get(request, *args, **kwargs)
            else:
                return HttpResponseRedirect(
                    reverse_lazy('profile_delete', kwargs={'pk': profile.pk, 'slug': profile.autoslug})
                )

    def delete(self, request, *args, **kwargs):
        """
        Deactivates the logged-in user and redirects to the logout URL.
        If called directly for a user with a profile, the profile (and all associated objects,
        such as places) will stay intact, dissimilar to the ProfileDeleteView's delete logic.
        """
        self.object = self.get_object()
        request.user.is_active = False
        request.user.save()
        messages.success(request, _("Farewell !"))
        return HttpResponseRedirect(self.get_success_url())


class FeedbackView(generic.View):
    """
    Provides the facility to submit feedback on a feature: either publicly to a
    board visible to others on the internet, or privately to the maintainers only.
    """
    template_names = {
        True: 'core/feedback_sent.html',
        False: 'core/feedback_form_fail.html',
    }

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        # Verify the form in the request; if it does not validate correctly,
        # it was most probably tampered with.
        form = FeedbackForm(data=QueryDict(request.body))
        if not form.is_valid():
            logging.getLogger('PasportaServo.ui.feedback').error(
                "Feedback form did not validate correctly; This most likely indicates tampering."
                + "\n\n %(errors)r \n\n Original submission: #%(message)s#.",
                {'errors': form.errors, 'message': form.data.get('message', "NULL")[:1000]},
                extra={'request': request},
            )
            if request.is_ajax():
                return JsonResponse({'result': False})
            else:
                return TemplateResponse(request, self.template_names[False])

        if form.cleaned_data['message']:
            self.request = request
            feedback_type = FEEDBACK_TYPES[form.cleaned_data['feedback_on']]
            message_text = form.cleaned_data['message']
            method = (
                self.submit_privately if form.cleaned_data['private']
                else self.submit_publicly
            )
            # Submit the feedback.
            method(feedback_type, message_text)
        if request.is_ajax():
            return JsonResponse({
                'result': True,
                'submitted': bool(form.cleaned_data['message']),
            })
        else:
            return TemplateResponse(
                request,
                self.template_names[True],
                {'submitted': bool(form.cleaned_data['message'])}
            )

    def submit_privately(self, feedback_type, message_text, exception=None):
        """
        Sends the feedback privately to the maintainers, including details of exception
        if occured during the public submission.
        """
        subject = gettext(
            # xgettext:python-brace-format
            "Feedback on {}."
        ).format(
            feedback_type.esperanto_name if str(get_language()).startswith('eo')
            else feedback_type.name
        )
        if self.request.user.is_authenticated:
            body = f'{gettext("User")} {self.request.user.pk} ({self.request.user.username}):'
        else:
            body = f'{Profile.INCOGNITO}:'
        body += '\n' + '-' * (len(body) - 1) + '\n\n'
        body += message_text
        if exception:
            error_notice = "During public submission, an exception has occured."
            error_notice += '\n\n'
            error_notice += '\n'.join(format_exception(None, exception, None))

        mail_admins(
            subject,
            body + (f'\n\n====\n{error_notice}' if exception else ''),
            fail_silently=False)

    def submit_publicly(self, feedback_type, message_text):
        """
        Posts the feedback publicly in a dedicated forum thread. In case an exception
        happens in the process, reverts to posting the feedback and the exception
        details privately to the maintainers.
        """
        transport = GQLHttpTransport(
            settings.GITHUB_GRAPHQL_HOST, auth=settings.GITHUB_ACCESS_TOKEN)
        client = GQLClient(transport=transport, fetch_schema_from_transport=True)

        # Attempt fetching the ID of the previous submission from the session.
        feedback_comment_id = self.request.session.get(f'feedback_{feedback_type.key}_comment_id')

        if feedback_comment_id:
            # If an ID is available, attempt fetching the contents of the previous
            # submission from the remote forum. (We do not persist the contents ourselves.)
            try:
                comment = client.execute(
                    gql("""
                        query($comment_id: ID!) {
                            node (id: $comment_id) { ... on DiscussionComment {
                                body
                            } }
                        }
                    """),
                    variable_values={'comment_id': feedback_comment_id})
            except (GraphQLError, TransportError, TransportQueryError):
                # Query failed for some reason, treat this as new submission.
                feedback_comment_id = None
                complete_text = message_text
            else:
                # Previous contents are available, concatenate them with the new feedback.
                complete_text = comment['node']['body'] + "\n\n----\n\n" + message_text

            # Perform an update GraphQL mutation.
            comment_query = gql("""
                mutation($comment_id: ID!, $body_text: String!) {
                    updateDiscussionComment (input: {commentId: $comment_id, body: $body_text}) {
                        comment { id url }
                    }
                }
            """)
            comment_query.operation = 'updateDiscussionComment'
            params = {'comment_id': feedback_comment_id, 'body_text': complete_text}

        if not feedback_comment_id:
            # Previous submission ID is not available, this is new submission.
            # Perform an insert GraphQL mutation.
            comment_query = gql("""
                mutation($disc_id: ID!, $body_text: String!) {
                    addDiscussionComment (input: {discussionId: $disc_id, body: $body_text}) {
                        comment { id url }
                    }
                }
            """)
            comment_query.operation = 'addDiscussionComment'
            complete_text = (
                '_`'
                + gettext("Sent from the website {env} ({user})").format(
                    env=settings.ENVIRONMENT if settings.ENVIRONMENT != 'PROD' else '',
                    user=self.request.user.pk or '/')
                + '`_ \n\n'
                + message_text
            )
            params = {'disc_id': feedback_type.foreign_id, 'body_text': complete_text}

        try:
            result = client.execute(comment_query, variable_values=params)
        except (GraphQLError, TransportError, TransportQueryError) as ex:
            # In case the query fails for some reason, let maintainers know that reason.
            self.submit_privately(feedback_type, message_text, ex)
        else:
            # Store the ID of the submission in the session, for future reuse.
            self.request.session[f'feedback_{feedback_type.key}_comment_id'] = (
                result[comment_query.operation]['comment']['id']
            )


class MassMailView(AuthMixin, generic.FormView):
    template_name = 'core/mass_mail_form.html'
    form_class = MassMailForm
    display_permission_denied = False
    exact_role = AuthRole.ADMIN
    # Keep the email address separate from the one used for transactional
    # emails, for better email sender reputation.
    mailing_address = 'anoncoj@pasportaservo.org'

    def dispatch(self, request, *args, **kwargs):
        kwargs['auth_base'] = None
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mailing_address'] = self.mailing_address
        return context

    def get_success_url(self):
        return format_lazy(
            '{success_url}?nb={sent}',
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
        default_from = f'Pasporta Servo <{self.mailing_address}>'
        template = get_template('email/mass_email.html')

        opening = make_aware(datetime(2014, 11, 24))
        profiles = Profile.objects_raw.none()

        if category == "not_hosts":
            # only active profiles, linked to existing user accounts
            profiles = Profile.objects_raw.filter(user__isnull=False, user__last_login__isnull=False)
            # exclude completely those who have at least one active available place
            profiles = profiles.exclude(owned_places__in=Place.objects_raw.filter(available=True))
            # remove profiles with places available in the past, that is deleted
            profiles = profiles.filter(Q(owned_places__available=False) | Q(owned_places__isnull=True))
        elif category == "old_system":
            # those who logged in before the opening date; essentially, never used the new system
            profiles = Profile.objects_raw.filter(user__last_login__lte=opening)
        elif category in ("in_book", "not_in_book"):
            # those who logged in after the opening date
            profiles = Profile.objects_raw.filter(user__last_login__gt=opening)
            # filter by active & available places according to 'in-book?' selection
            places_in_book = Place.objects_raw.filter(
                owner=OuterRef('pk'), in_book=True, available=True)
            places_not_in_book = Place.objects_raw.filter(
                owner=OuterRef('pk'), in_book=False, available=True)
            if category == "in_book":
                profiles = profiles.filter(Exists(places_in_book))
            elif category == "not_in_book":  # pragma: no branch
                profiles = profiles.filter(Exists(places_not_in_book) & ~Exists(places_in_book))
        elif category in ("users_active_1y", "users_active_2y"):
            # profiles active in the last 1 or 2 years (and linked to existing user accounts)
            cutoff = make_aware(datetime.today())
            cutoff = cutoff - timedelta(days=365 if category == "users_active_1y" else 730)
            profiles = Profile.objects_raw.filter(user__last_login__gte=cutoff)
        # ensure that the account is still active and the person is not deceased
        profiles = profiles.filter(user__is_active=True, death_date__isnull=True)
        # finally remove duplicates
        profiles = profiles.distinct()
        # leave only the needed fields
        profiles = profiles.select_related('user').only(
            'first_name', 'last_name', 'user__username', 'user__email',
        )

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
                [test_email],
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
                [value_without_invalid_marker(profile.user.email)],
            ) for profile in profiles]

        self.nb_sent = send_mass_html_mail(messages)
        return super().form_valid(form)


class MassMailSentView(AuthMixin, generic.TemplateView):
    template_name = 'core/mass_mail_sent.html'
    display_permission_denied = False
    exact_role = AuthRole.ADMIN

    def dispatch(self, request, *args, **kwargs):
        kwargs['auth_base'] = None
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nb'] = (
            int(self.request.GET['nb'])
            if self.request.GET.get('nb', '').isdigit()
            else None
        )
        return context


class HtmlFragmentRetrieveView(generic.TemplateView):
    template_names = {
        'mailto_fallback': 'ui/fragment-mailto_fallback.html',
        'datalist_fallback': 'ui/fragment-datalist_fallback.html',
        'place_country_region_formfield': 'ui/fragment-subregion_formfield.html',
    }

    def get(self, request, *args, **kwargs):
        self.fragment_id = kwargs['fragment_id']
        if self.fragment_id not in self.template_names:
            raise Http404("Unknown HTML Fragment")
        if self.fragment_id.endswith('fallback'):
            logging.getLogger('PasportaServo.ui.fallbacks').warning(
                f"The {self.fragment_id} was used", extra={'request': request}
            )

        if self.fragment_id == 'place_country_region_formfield':
            country = request.GET.get('country')
            subform = SubregionForm(Place, 'state_province', for_country=country)
            subform.helper.disable_csrf = True
            self.extra_context = {'form': subform}

        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        return [self.template_names[self.fragment_id]]
