from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    PasswordResetForm, SetPasswordForm, UserCreationForm,
)
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.core.mail import send_mail
from django.db.models import Q, Value as V
from django.db.models.functions import Concat
from django.template.loader import get_template
from django.utils.translation import pgettext_lazy, ugettext_lazy as _

from hosting.models import Profile
from hosting.utils import value_without_invalid_marker
from links.utils import create_unique_url

from .models import SiteConfiguration

User = get_user_model()


class SystemEmailFormMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Stores the value before the change.
        self.previous_email = value_without_invalid_marker(self.instance.email)

    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            raise forms.ValidationError(_("Enter a valid email address."))
        invalid_email = Concat(V(settings.INVALID_PREFIX), V(email))
        emails_lookup = Q(email=email) | Q(email=invalid_email)
        if email and email != self.previous_email and User.objects.filter(emails_lookup).exists():
            raise forms.ValidationError(_("User address already in use."))
        return email


class UserRegistrationForm(SystemEmailFormMixin, UserCreationForm):
    email = forms.EmailField(
        label=_("Email address"), max_length=254)
    # Honeypot:
    name = forms.CharField(
        widget=forms.TextInput(attrs={'autocomplete': 'off'}),
        required=False,
        help_text=_("Leave blank"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User._meta.get_field('email')._unique = True
        for fieldname in ['username', 'password1', 'password2', 'email']:
            self.fields[fieldname].help_text = None
            self.fields[fieldname].widget.attrs['placeholder'] = self.fields[fieldname].label

    def clean_name(self):
        """Remove flies from the honeypot."""
        flies = self.cleaned_data['name']
        if flies:
            raise forms.ValidationError("")
        return flies

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
    save.alters_data = True


class UsernameUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']

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


class SystemPasswordResetForm(SetPasswordForm):
    def save(self, commit=True):
        super().save(commit)
        if commit:
            Profile.mark_valid_emails([self.user.email])
        return self.user
    save.alters_data = True


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
