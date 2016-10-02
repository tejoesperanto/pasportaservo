from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm as UserLoginForm, UserCreationForm
from django.contrib.auth import get_user_model

from django_countries import countries
from phonenumber_field.formfields import PhoneNumberField

from .models import Profile, Place, Phone, Condition


User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label=_("Email"), max_length=254)
    # Honeypot:
    name = forms.CharField(widget=forms.TextInput(attrs={'autocomplete':'off'}),
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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'title',
            'first_name',
            'last_name',
            'birth_date',
            'description',
            'avatar',
        ]

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['birth_date'].widget.attrs['placeholder'] = 'jjjj-mm-tt'

    def clean(self):
        """Sets some fields as required if user wants his data to be printed in book."""
        cleaned_data = super(ProfileForm, self).clean()
        if hasattr(self, 'instance'):
            profile = self.instance
            in_book = any([place.in_book for place in profile.owned_places.all()])
            required_fields = ['title', 'first_name', 'last_name']
            all_filled = all([cleaned_data[field] for field in required_fields])
            message = _("You want to be in the printed edition of Pasporta Servo. "
                        "In order to have a quality product, some fields a required. "
                        "If you think there is a problem, please contact us.")

            if in_book and not all_filled:
                msg = _("This field is required to be printed in the book.")
                for field in required_fields:
                    if not cleaned_data[field]:
                        self.add_error(field, msg)
                raise forms.ValidationError(message)
        return cleaned_data


class ProfileCreateForm(ProfileForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(ProfileCreateForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        profile = super(ProfileForm, self).save(commit=False)
        profile.user = self.user
        if commit:
            profile.save()
        return profile


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = [
            'closest_city',
            'address',
            'city',
            'postcode',
            'state_province',
            'country',
            'max_guest', 'max_night', 'contact_before',
            'description', 'short_description',
            'available',
            'tour_guide', 'have_a_drink',
            'sporadic_presence',
            'in_book',
            'conditions',
            'latitude', 'longitude',
        ]

    def __init__(self, *args, **kwargs):
        super(PlaceForm, self).__init__(*args, **kwargs)
        self.fields['conditions'].help_text = ""
        self.fields['conditions'].widget.attrs['data-placeholder'] = _("Choose your conditions...")

    def clean(self):
        """Sets some fields as required if user wants his data to be printed in book."""
        cleaned_data = super(PlaceForm, self).clean()
        required_fields = ['address', 'city', 'postcode', 'country',
            'short_description', 'available', 'latitude', 'longitude']
        all_filled = all([cleaned_data.get(field, False) for field in required_fields])
        message = _("You want to be in the printed edition of Pasporta Servo. "
                    "In order to have a quality product, some fields a required. "
                    "If you think there is a problem, please contact us.")

        if cleaned_data['in_book'] and not all_filled:
            for field in required_fields:
                if not cleaned_data['latitude'] or not cleaned_data['longitude']:
                    raise forms.ValidationError(_("Please click on the map to choose your location."))
                if not cleaned_data.get(field, False):
                    self.add_error(field, _("This field is required to be printed in the book."))
            raise forms.ValidationError(message)
        return cleaned_data


class PlaceCreateForm(PlaceForm):
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        super(PlaceCreateForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        place = super(PlaceForm, self).save(commit=False)
        place.owner = self.profile
        if commit:
            place.save()
        return place


class PhoneForm(forms.ModelForm):
    class Meta:
        model = Phone
        fields = ['number', 'type', 'country', 'comments']

    def __init__(self, *args, **kwargs):
        super(PhoneForm, self).__init__(*args, **kwargs)
        if not hasattr(self, 'profile'):
            self.profile = self.instance.profile
        self.fields['number'].widget.input_type = 'tel'

    def clean(self):
        """Checks if the number and the profile are unique together."""
        cleaned_data = super(PhoneForm, self).clean()
        if 'number' in cleaned_data:
            data = cleaned_data['number'].as_e164
            phones = Phone.objects.filter(number=data, profile=self.profile)
            number_list = phones.values_list('number', flat=True)
            if data in number_list:
                # Check is done for object creation and object update
                if self.instance.number is None or data != self.instance.number.as_e164:
                    self.add_error('number', _("You already have this telephone number."))
        return cleaned_data


class PhoneCreateForm(PhoneForm):
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        super(PhoneCreateForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        phone = super(PhoneCreateForm, self).save(commit=False)
        phone.profile = self.profile
        if commit:
            phone.save()
        return phone


class AuthorizeUserForm(forms.Form):
    user = forms.CharField(label=_("Authorize user"), max_length=254)
    remove = forms.BooleanField(required=False, initial=False, widget=forms.widgets.HiddenInput)

    def __init__(self, *args, **kwargs):
        super(AuthorizeUserForm, self).__init__(*args, **kwargs)
        self.fields['user'].widget.attrs['placeholder'] = _("username")

    def clean(self):
        cleaned_data = super(AuthorizeUserForm, self).clean()
        if 'user' not in cleaned_data:
            return
        user_qualifier = cleaned_data['user']
        if not cleaned_data.get('remove', False):
            try:
                User.objects.get(username=user_qualifier).profile
            except User.DoesNotExist:
                raise forms.ValidationError(_("User does not exist"))
            except Profile.DoesNotExist:
                raise forms.ValidationError(_("User has not set up a profile"))
        return cleaned_data


class AuthorizedOnceUserForm(AuthorizeUserForm):
    def __init__(self, *args, **kwargs):
        super(AuthorizedOnceUserForm, self).__init__(*args, **kwargs)
        self.fields['user'].widget = forms.widgets.HiddenInput()
        self.fields['remove'].initial = True


class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['title', 'first_name', 'last_name', 'birth_date']


class FamilyMemberCreateForm(FamilyMemberForm):
    def __init__(self, *args, **kwargs):
        self.place = kwargs.pop('place')
        super(FamilyMemberForm, self).__init__(*args, **kwargs)

    def save(self):
        family_member = super(FamilyMemberForm, self).save()
        self.place.family_members.add(family_member)
        return family_member


class MassMailForm(forms.Form):
    subject = forms.CharField(label=_("Subject"), initial="[Pasporta Servo] ")
    body = forms.CharField(label=_("Body"), widget=forms.Textarea, initial="Kara {nomo},")
    categories = forms.ChoiceField(label=_("Categories"), choices=(
        ('test', _("test")),
        ('old_system', _("old system")),
        ('not_in_book', _("not in book")),
        ('in_book', _("in book")),
        ('just_user', _("just user")),
    ))
    test_email = forms.EmailField(label=_("Your email for test"), initial="baptiste@darthenay.fr")
