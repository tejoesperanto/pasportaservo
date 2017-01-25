from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q, Value as V
from django.db.models.functions import Concat
from django.core.mail import send_mail
from django.template.loader import get_template
from django.template import Context
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from links.utils import create_unique_url

User = get_user_model()


class SystemEmailFormMixin(object):
    def __init__(self, *args, **kwargs):
        super(SystemEmailFormMixin, self).__init__(*args, **kwargs)
        self.previous_email = (self.instance.email[len(settings.INVALID_PREFIX):]
                               if self.instance.email.startswith(settings.INVALID_PREFIX)
                               else self.instance.email) # value before the change

    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            raise forms.ValidationError(_("Enter a valid email address."))
        invalid_email = Concat(V(settings.INVALID_PREFIX), V(email))
        emails_lookup = Q(email=email) | Q(email=invalid_email)
        if email and email != self.previous_email and User.objects.filter(emails_lookup):
            raise forms.ValidationError(_("User address already in use."))
        return email


class UserRegistrationForm(SystemEmailFormMixin, UserCreationForm):
    email = forms.EmailField(label=_("Email"), max_length=254)
    # Honeypot:
    name = forms.CharField(widget=forms.TextInput(attrs={'autocomplete': 'off'}),
        help_text=_("Leave blank"), required=False)

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
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
        user = super(UserRegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class UsernameUpdateForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['username']


class EmailUpdateForm(SystemEmailFormMixin, forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['email']

    def __init__(self, *args, **kwargs):
        super(EmailUpdateForm, self).__init__(*args, **kwargs)
        self.initial['email'] = self.previous_email # display the clean value

    def save(self):
        """ Saves nothing but sends a warning email to old email address,
            and sends a confirmation link to the new email address.
        """
        old_email = self.previous_email
        new_email = self.cleaned_data['email']
        if old_email == new_email:
            return self.instance

        url = create_unique_url({
            'action': 'email_update',
            'pk': self.instance.pk,
            'email': new_email,
        })
        context = Context({
            'site_name': settings.SITE_NAME,
            'url': url,
            'user': self.instance,
            'email': new_email,
        })
        subject = _("[Pasporta Servo] Change of email address")
        for old_new in ['old', 'new']:
            message = get_template('email/%s_email_update.txt' % old_new)
            html_message = get_template('email/%s_email_update.html' % old_new)
            send_mail(
                subject,
                message.render(context),
                settings.DEFAULT_FROM_EMAIL,
                recipient_list=[{'old': old_email, 'new': new_email}[old_new]],
                html_message=html_message.render(context),
                fail_silently=False)

        return self.instance


class StaffUpdateEmailForm(SystemEmailFormMixin, forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['email']


class MassMailForm(forms.Form):
    heading = forms.CharField(label=_("Heading"), initial="Anonco")
    body = forms.CharField(label=_("Body"), widget=forms.Textarea, initial="Kara {nomo},\n\n")
    subject = forms.CharField(label=_("Subject"), initial=_("Subject"))
    preheader = forms.CharField(label=_("Preheader"), max_length=100,
        widget=forms.Textarea(attrs={'rows': 2}))
    categories = forms.ChoiceField(label=_("Categories"), choices=(
        ('test', _("test")),
        ('old_system', _("old system")),
        ('not_in_book', _("not in book")),
        ('in_book', _("in book")),
        ('just_user', _("just user")),
    ))
    test_email = forms.EmailField(label=_("Your email for test"), initial="baptiste@darthenay.fr")
