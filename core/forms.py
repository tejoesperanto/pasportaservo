from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
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

    def clean_email(self):
        email = self.cleaned_data['email']
        if email and User.objects.filter(email=email):
            raise forms.ValidationError(_("User address already in use."))
        return email

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


class StaffUpdateEmailForm(forms.ModelForm):
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