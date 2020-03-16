import logging

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    PasswordChangeForm, PasswordResetForm, SetPasswordForm, UserCreationForm,
)
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.mail import send_mail
from django.db.models import Q, Value as V
from django.db.models.functions import Concat, Lower
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils.translation import pgettext_lazy, ugettext_lazy as _

from hosting.models import Profile
from hosting.utils import value_without_invalid_marker
from links.utils import create_unique_url

from .models import SiteConfiguration
from .utils import is_password_compromised

User = get_user_model()


auth_log = logging.getLogger('PasportaServo.auth')


class UsernameFormMixin(object):
    username_error_messages = {
        # We do not want to disclose the exact usernames in the system through
        # the error messages, and thus facilitate user enumeration attacks...
        'unique': _("A user with a similar username already exists."),
        # Clearly spell out to the potential new users what a valid username is.
        'invalid': mark_safe(_(
            "Enter a username conforming to these rules: "
            " This value may contain only letters, numbers, and the symbols"
            " <kbd>@</kbd> <kbd>.</kbd> <kbd>+</kbd> <kbd>-</kbd> <kbd>_</kbd>."
            " Spaces are not allowed."
        )),
        # Indicate what are the limitations in terms of number of characters.
        'max_length': _(
            "Ensure that this value has at most %(limit_value)d characters "
            "(it has now %(show_value)d)."
        ),
    }

    def clean_username(self):
        """
        Ensure that the username provided is unique (in a case-insensitive manner).
        This check replaces the Django's built-in uniqueness verification.
        """
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(self._meta.error_messages['username']['unique'])
        return username


class SystemEmailFormMixin(object):
    email_error_messages = {
        'max_length': _(
            "Ensure that this value has at most %(limit_value)d characters "
            "(it has now %(show_value)d)."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Stores the value before the change.
        self.previous_email = value_without_invalid_marker(self.instance.email)

    def clean_email(self):
        """
        Ensure that the email address provided is unique (in a case-insensitive manner).
        """
        email_value = self.cleaned_data['email']
        if not email_value:
            raise forms.ValidationError(_("Enter a valid email address."))
        invalid_email = Concat(V(settings.INVALID_PREFIX), V(email_value))
        emails_lookup = Q(email_lc=V(email_value.lower())) | Q(email__iexact=invalid_email)
        if email_value and email_value.lower() != self.previous_email.lower() \
                and User.objects.annotate(email_lc=Lower('email')).filter(emails_lookup).exists():
            raise forms.ValidationError(_("User address already in use."))
        return email_value


class PasswordFormMixin(object):
    def analyze_password(self, password_field_value):
        insecure, howmuch = is_password_compromised(password_field_value)

        if insecure and howmuch > 99:
            self.add_error(NON_FIELD_ERRORS, forms.ValidationError(_(
                "The password selected by you is too insecure. "
                "Such combination of characters is very well-known to cyber-criminals."),
                code='compromised_password'))
            self.add_error(self.analyze_password_field, _("Choose a less easily guessable password."))
        elif insecure and howmuch > 1:
            self.add_error(NON_FIELD_ERRORS, forms.ValidationError(_(
                "The password selected by you is not very secure. "
                "Such combination of characters is known to cyber-criminals."),
                code='compromised_password'))
            self.add_error(self.analyze_password_field, _("Choose a less easily guessable password."))

        if insecure:
            auth_log.warning(
                "Password with HIBP count {:d} selected in {}.".format(howmuch, self.__class__.__name__),
                extra={'request': self.view_request} if hasattr(self, 'view_request') else None,
            )

    def clean(self):
        cleaned_data = super().clean()
        if self.analyze_password_field in cleaned_data:
            self.analyze_password(cleaned_data[self.analyze_password_field])
        return cleaned_data


class UserRegistrationForm(UsernameFormMixin, PasswordFormMixin, SystemEmailFormMixin, UserCreationForm):
    email = forms.EmailField(
        label=_("Email address"), max_length=254)
    # Honeypot:
    realm = forms.CharField(
        widget=forms.TextInput(attrs={'autocomplete': 'off'}),
        required=False,
        help_text=_("Protection against automated registrations. "
                    "Make sure that this field is kept completely blank."))

    class Meta(UserCreationForm.Meta):
        error_messages = {
            'email': SystemEmailFormMixin.email_error_messages,
            'username': UsernameFormMixin.username_error_messages,
        }
    analyze_password_field = 'password1'

    def __init__(self, *args, **kwargs):
        self.view_request = kwargs.pop('view_request', None)
        super().__init__(*args, **kwargs)

        User._meta.get_field('email')._unique = True
        for fieldname in ['username', 'password1', 'password2', 'email']:
            self.fields[fieldname].help_text = None
            self.fields[fieldname].widget.attrs['placeholder'] = self.fields[fieldname].label

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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
    save.alters_data = True


class UsernameUpdateForm(UsernameFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        error_messages = {'username': UsernameFormMixin.username_error_messages}

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save(update_fields=['username'])
        return user
    save.alters_data = True


class EmailUpdateForm(SystemEmailFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        error_messages = {'email': SystemEmailFormMixin.email_error_messages}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Displays the clean value of the address in the form.
        self.initial['email'] = self.previous_email

    def save(self):
        """
        Saves nothing but sends a warning email to old email address,
        and sends a confirmation link to the new email address.
        """
        config = SiteConfiguration.get_solo()
        old_email = self.previous_email
        new_email = self.cleaned_data['email']
        if old_email == new_email:
            return self.instance

        url = create_unique_url({
            'action': 'email_update',
            'v': False,
            'pk': self.instance.pk,
            'email': new_email,
        })
        context = {
            'site_name': config.site_name,
            'url': url,
            'user': self.instance,
            'email': new_email,
        }
        subject = _("[Pasporta Servo] Change of email address")
        for old_new in ['old', 'new']:
            email_template_text = get_template('email/{type}_email_update.txt'.format(type=old_new))
            email_template_html = get_template('email/{type}_email_update.html'.format(type=old_new))
            send_mail(
                subject,
                email_template_text.render(context),
                settings.DEFAULT_FROM_EMAIL,
                recipient_list=[{'old': old_email, 'new': new_email}[old_new]],
                html_message=email_template_html.render(context),
                fail_silently=False)

        return self.instance
    save.do_not_call_in_templates = True


class EmailStaffUpdateForm(SystemEmailFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Displays the clean value of the address in the form.
        self.initial['email'] = self.previous_email

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save(update_fields=['email'])
        return user
    save.alters_data = True


class SystemPasswordResetRequestForm(PasswordResetForm):
    def get_users(self, email):
        """
        Given an email address, returns a matching user who should receive
        a reset message.
        """
        active_users = User._default_manager.filter(is_active=True)
        invalid_email = Concat(V(settings.INVALID_PREFIX), V(email))
        lookup_users = active_users.filter(Q(email__iexact=email) | Q(email__iexact=invalid_email))

        def remove_invalid_prefix(user):
            user.email = value_without_invalid_marker(user.email)
            return user

        # All users should be able to reset their passwords regardless of the hashing (even when obsoleted),
        # unless the password was forcefully set by an administrator as unusable to prevent logging in.
        return map(remove_invalid_prefix, (
            u for u in lookup_users
            if u.password is not None and not u.password.startswith(UNUSABLE_PASSWORD_PREFIX)
        ))


class SystemPasswordResetForm(PasswordFormMixin, SetPasswordForm):
    analyze_password_field = 'new_password1'

    def save(self, commit=True):
        super().save(commit)
        if commit:
            Profile.mark_valid_emails([self.user.email])
        return self.user
    save.alters_data = True


class SystemPasswordChangeForm(PasswordFormMixin, PasswordChangeForm):
    analyze_password_field = 'new_password1'


class MassMailForm(forms.Form):
    heading = forms.CharField(
        label=_("Heading"), initial=_("Announcement"))
    body = forms.CharField(
        label=_("Body"), initial=_("Dear {nomo},\n\n"),
        widget=forms.Textarea)
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
            ('just_user', pgettext_lazy("Mass mailing category", "just user")),
        )
    )
    test_email = forms.EmailField(
        label=_("Your email for test"), initial="baptiste@darthenay.fr")
