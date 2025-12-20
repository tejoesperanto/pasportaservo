from datetime import datetime
from typing import Any, cast
from uuid import uuid4

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm,
    PasswordResetForm, SetPasswordForm, UserCreationForm,
)
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.core.mail import send_mail
from django.db.models import Manager, Q
from django.template.loader import get_template
from django.urls import reverse
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from anymail.exceptions import AnymailRecipientsRefused
from crispy_forms.helper import FormHelper
from django_q.tasks import async_task

from core.utils import camel_case_split
from hosting.models import PasportaServoUser, Profile
from hosting.utils import value_without_invalid_marker
from links.utils import create_unique_url

from .auth import auth_log
from .mixins import (
    HtmlIdFormMixin, PasswordFormMixin,
    SystemEmailFormMixin, UsernameFormMixin,
)
from .models import FEEDBACK_TYPES, SiteConfiguration
from .widgets import PasswordWithToggleInput

User = get_user_model()


class UserRegistrationForm(
        UsernameFormMixin, PasswordFormMixin, SystemEmailFormMixin,
        HtmlIdFormMixin, UserCreationForm):
    # Honeypot:
    realm = forms.CharField(
        widget=forms.TextInput(attrs={'autocomplete': 'off'}),
        required=False,
        help_text=_("Protection against automated registrations. "
                    "Make sure that this field is kept completely blank."))

    class Meta(UserCreationForm.Meta):
        fields = ['username', 'email']
        error_messages = {
            'email': SystemEmailFormMixin.email_error_messages,
            'username': UsernameFormMixin.username_error_messages,
        }
    field_order = ['username', 'password1', 'password2', 'email']
    analyze_password_field = 'password1'

    def __init__(self, *args, **kwargs):
        self.view_request = kwargs.pop('view_request', None)
        super().__init__(*args, **kwargs)

        self.fields['email'].required = True
        for fieldname in ['password1', 'password2', 'email']:
            self.fields[fieldname].help_text = None
        self.fields['username'].help_text = _(
            "Capital and small letters are treated as different. Do not use spaces."
        )
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        self.fields['password1'].widget = PasswordWithToggleInput(
            attrs=self.fields['password1'].widget.attrs | {'autocomplete': 'new-password'},
        )
        self.fields['password2'].widget = PasswordWithToggleInput(
            attrs=self.fields['password2'].widget.attrs | {'autocomplete': 'new-password'},
        )

    def clean_realm(self):
        """
        Remove flies from the honeypot.
        """
        flies = self.cleaned_data['realm']
        if flies:
            auth_log.error(
                "Registration failed, flies found in honeypot.",
                extra={'request': self.view_request},
            )
            raise forms.ValidationError("")
        return flies

    @property
    def proxy_user(self):
        """
        Returns an object that looks like a User but proxies value queries to
        the cleaned data of the form.
        """
        class ProxyUser:
            @property
            def _meta(proxy):
                return self._meta.model._meta

            def __getattr__(proxy, attr):
                try:
                    if attr == 'profile':
                        raise Profile.DoesNotExist
                    return self.cleaned_data.get(attr)
                except AttributeError:
                    raise AttributeError("Form was not cleaned yet")

        return ProxyUser()

    def save(self, **kwargs):
        return super().save(**kwargs)
    save.alters_data = True


class UserAuthenticationForm(HtmlIdFormMixin, AuthenticationForm):
    admin_inactive_user_notification = "User '{u.username}' tried to log in"

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.error_messages['invalid_login'] = _(
            "Please enter the correct username and password. "
            "Note that both fields are case-sensitive "
            "('aBc' is different from 'abc')."
        )
        self.helper = FormHelper(self)
        # The form errors should be rendered in small font.
        self.helper.form_error_class = 'small'
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        self.fields['password'].widget = PasswordWithToggleInput(
            attrs=self.fields['password'].widget.attrs | {'autocomplete': 'current-password'},
        )

    def confirm_login_allowed(self, user):
        """
        Allow full login by active users, and inform inactive users that their
        account is disabled and they can request and admin to re-enable it.
        """
        if not user.is_active:
            case_id = str(uuid4()).upper()
            auth_log.warning(
                (self.admin_inactive_user_notification + ", but the account is deactivated [{cid}].")
                .format(u=user, cid=case_id)
            )
            self.request.session['restore_request_id'] = (case_id, datetime.now().timestamp())
            raise forms.ValidationError([
                forms.ValidationError(
                    self.error_messages['inactive'],
                    code='inactive',
                ),
                forms.ValidationError(
                    _("Would you like to re-enable it? <a href=\"%(url)s\">Inform an administrator.</a>"),
                    code='restore_hint',
                    params={'url': reverse('login_restore')},
                ),
            ])


class UsernameUpdateForm(UsernameFormMixin, HtmlIdFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        error_messages = {'username': UsernameFormMixin.username_error_messages}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['autofocus'] = True

    def save(self, **kwargs):
        return super().save(**kwargs)
    save.alters_data = True


class EmailUpdateForm(SystemEmailFormMixin, HtmlIdFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        error_messages = {'email': SystemEmailFormMixin.email_error_messages}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['autofocus'] = True
        # Displays the clean value of the address in the form.
        self.initial['email'] = self.previous_email

    def save(self, commit=True):
        """
        Saves nothing but sends a warning email to old email address,
        and sends a confirmation link to the new email address.
        """
        config = SiteConfiguration.get_solo()
        old_email = self.previous_email
        new_email = self.cleaned_data['email']
        if old_email == new_email:
            return self.instance

        url, token = create_unique_url({
            'action': 'email_update',
            'v': False,
            'pk': self.instance.pk,
            'email': new_email,
        })
        context = {
            'site_name': config.site_name,
            'ENV': settings.ENVIRONMENT,
            'RICH_ENVELOPE': getattr(settings, 'EMAIL_RICH_ENVELOPES', None),
            'subject_prefix': settings.EMAIL_SUBJECT_PREFIX_FULL,
            'url': url,
            'url_first': url[:url.rindex('/')+1],
            'url_second': token,
            'user': self.instance,
            'email': new_email,
        }
        for old_new in ['old', 'new']:
            email_template_subject = get_template(f'email/{old_new}_email_subject.txt')
            email_template_text = get_template(f'email/{old_new}_email_update.txt')
            email_template_html = get_template(f'email/{old_new}_email_update.html')
            try:
                send_mail(
                    # No newlines are allowed in subject.
                    ''.join(email_template_subject.render(context).splitlines()),
                    email_template_text.render(context),
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[{'old': old_email, 'new': new_email}[old_new]],
                    html_message=email_template_html.render(context),
                    fail_silently=False,
                )
            except AnymailRecipientsRefused:
                # The recipient was rejected by the ESP. For the old email address,
                # which might already be invalid, do nothing. For the new one, inform
                # the user that there is a problem with the mailbox.
                if old_new == 'new':
                    raise forms.ValidationError(
                        _(
                            "This new email address cannot be reached. Please check for typos and "
                            "problems with this mailbox. If you believe this is incorrect, please "
                            "<a href=\"%(url)s\">contact us</a>."
                        ),
                        code='rejected',
                        params={'url': f'mailto:{settings.SUPPORT_EMAIL}'},
                    )

        return self.instance
    save.do_not_call_in_templates = True


class EmailStaffUpdateForm(SystemEmailFormMixin, HtmlIdFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        error_messages = {'email': SystemEmailFormMixin.email_error_messages}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['autofocus'] = True
        # Displays the clean value of the address in the form.
        self.initial['email'] = self.previous_email

    def save(self, **kwargs):
        return super().save(**kwargs)
    save.alters_data = True


class SystemPasswordResetRequestForm(HtmlIdFormMixin, PasswordResetForm):
    admin_inactive_user_notification = "User '{u.username}' tried to reset the login password"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['autofocus'] = True

    def get_users(self, email):
        """
        Given an email address, returns a matching user who should receive
        a reset message.
        """
        users = User._default_manager.filter()
        invalid_email = f'{settings.INVALID_PREFIX}{email}'
        lookup_users = cast(
            Manager[PasportaServoUser],
            users.filter(Q(email__iexact=email) | Q(email__iexact=invalid_email)))

        def remove_invalid_prefix(user: PasportaServoUser):
            user.email = value_without_invalid_marker(user.email)
            return user

        # All users should be able to reset their passwords regardless of the hashing
        # algorithm (even when obsoleted) – unless the password was forcefully set by
        # an administrator as unusable to prevent logging in.
        return map(remove_invalid_prefix, (
            u for u in lookup_users
            if u.password is not None and not u.password.startswith(UNUSABLE_PASSWORD_PREFIX)
        ))

    def send_mail(
            self,
            subject_template_name: str,
            email_template_name: dict[bool, str],
            context: dict[str, Any],
            *args,
            html_email_template_name: dict[bool, str],
            **kwargs,
    ):
        user_is_active = context['user'].is_active
        template_name_html = html_email_template_name[user_is_active]
        template_name_plain = email_template_name[user_is_active]
        if not user_is_active:
            case_id = str(uuid4()).upper()
            async_task(
                auth_log.warning,
                (self.admin_inactive_user_notification + ", but the account is deactivated [{cid}].")
                .format(u=context['user'], cid=case_id),
                group='inactive account',
            )
            context['restore_request_id'] = case_id

        args = [subject_template_name, template_name_plain, context, *args]
        kwargs.update(
            template_name_content_html=template_name_html,
            bounce_notification=(
                (self.admin_inactive_user_notification + ", but the email address bounces.")
                .format(u=context['user'])
            ),
        )
        context.update({
            'ENV': settings.ENVIRONMENT,
            'RICH_ENVELOPE': getattr(settings, 'EMAIL_RICH_ENVELOPES', None),
            'subject_prefix': settings.EMAIL_SUBJECT_PREFIX_FULL,
        })
        async_task(
            self.send_out_of_band_email, *args, **kwargs,
            group=' '.join(camel_case_split(self.__class__.__name__)[:-2]).lower(),
        )

    @staticmethod
    def send_out_of_band_email(
            template_name_subject: str,
            template_name_content_plain: str,
            context: dict[str, Any],
            from_email: str | None,
            to_email: str,
            template_name_content_html: str,
            bounce_notification: str,
    ):
        try:
            # No newlines are allowed in subject.
            subject = ''.join(
                get_template(template_name_subject).render(context).splitlines())
            send_mail(
                subject,
                get_template(template_name_content_plain).render(context),
                from_email,
                recipient_list=[to_email],
                html_message=get_template(template_name_content_html).render(context),
                fail_silently=False,
            )
        except AnymailRecipientsRefused:
            auth_log.warning(bounce_notification)

    def save(self, **kwargs):
        return super().save(**kwargs)
    save.do_not_call_in_templates = True


class SystemPasswordResetForm(PasswordFormMixin, HtmlIdFormMixin, SetPasswordForm):
    analyze_password_field = 'new_password1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget = PasswordWithToggleInput(
            attrs=self.fields['new_password1'].widget.attrs | {'autocomplete': 'new-password'},
        )
        self.fields['new_password2'].widget = PasswordWithToggleInput(
            attrs=self.fields['new_password2'].widget.attrs | {'autocomplete': 'new-password'},
        )

    def save(self, commit=True):
        super().save(commit)
        if commit:
            Profile.mark_valid_emails([self.user.email])
        return self.user
    save.alters_data = True


class SystemPasswordChangeForm(PasswordFormMixin, HtmlIdFormMixin, PasswordChangeForm):
    analyze_password_field = 'new_password1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget = PasswordWithToggleInput(
            attrs=self.fields['old_password'].widget.attrs | {'autocomplete': 'current-password'},
        )
        self.fields['new_password1'].widget = PasswordWithToggleInput(
            attrs=self.fields['new_password1'].widget.attrs | {'autocomplete': 'new-password'},
        )
        self.fields['new_password2'].widget = PasswordWithToggleInput(
            attrs=self.fields['new_password2'].widget.attrs | {'autocomplete': 'new-password'},
        )

    def save(self, **kwargs):
        return super().save(**kwargs)
    save.alters_data = True


class UsernameRemindRequestForm(SystemPasswordResetRequestForm):
    admin_inactive_user_notification = "User '{u.username}' requested a reminder of the username"


class FeedbackForm(forms.Form):
    message = forms.CharField(
        label=_("Message"),
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'vertically-expandable'}),
        help_text=_("Your contribution will appear in a discussion thread "
                    "publicly visible on {forum_url}, without your name."))
    private = forms.BooleanField(
        label=_("Contribute privately."),
        required=False)
    feedback_on = forms.ChoiceField(
        choices=[(key, None) for key in FEEDBACK_TYPES.keys()],
        widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_class = 'sr-only'

        self.fields['feedback_on'].initial = next(iter(FEEDBACK_TYPES.keys()))
        self.fields['message'].widget.attrs['autofocus'] = True
        discussion_url = (
            FEEDBACK_TYPES[self.fields['feedback_on'].initial].url
            or settings.GITHUB_DISCUSSION_BASE_URL
        )
        self.fields['message'].help_text = format_lazy(
            self.fields['message'].help_text,
            forum_url=f'<a href="{discussion_url}"'
                      '  target="_blank" rel="external noreferrer">GitHub</a>'
        )


class MassMailForm(forms.Form):
    prefix = "massmail"

    heading = forms.CharField(
        label=_("Heading"), initial=_("Announcement"))
    body = forms.CharField(
        label=_("Body"), initial=_("Dear {nomo},\n\n"),
        widget=forms.Textarea(attrs={'class': 'vertically-expandable'}))
    subject = forms.CharField(
        label=_("Subject"), initial=_("Subject"))
    preheader = forms.CharField(
        label=_("Preheader"),
        max_length=100,
        widget=forms.Textarea(attrs={'rows': 2}))
    categories = forms.ChoiceField(
        label=_("Categories"),
        choices=(
            ('test', pgettext_lazy("Mass mailing category", "test")),
            ('old_system', pgettext_lazy("Mass mailing category", "old system")),
            ('not_in_book', pgettext_lazy("Mass mailing category", "not in book")),
            ('in_book', pgettext_lazy("Mass mailing category", "in book")),
            ('not_hosts', pgettext_lazy("Mass mailing category", "not hosts")),
            ('users_active_1y', pgettext_lazy("Mass mailing category", "active users (1 year)")),
            ('users_active_2y', pgettext_lazy("Mass mailing category", "active users (2 years)")),
        )
    )
    test_email = forms.EmailField(
        label=_("Your email for test"), initial="baptiste@darthenay.fr")
