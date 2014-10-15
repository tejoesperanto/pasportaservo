from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm as UserLoginForm, UserCreationForm
from django.contrib.auth.models import User

from django_countries import countries
from phonenumber_field.formfields import PhoneNumberField

from .models import Profile, Place, Phone, Condition


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label=_("Email"), max_length=254)
    # Honeypot:
    name = forms.CharField(required=False, help_text=_("Leave blank"))

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
        self.user = kwargs.pop('user')
        super(ProfileForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        profile = super(ProfileForm, self).save(commit=False)
        profile.user = self.user
        if commit:
            profile.save()
        return profile


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = [
            'address',
            'city',
            'postcode',
            'country',
            'closest_city',
            'max_host', 'max_night', 'contact_before',
            'description', 'short_description',
            'booked', 'available',
            'tour_guide', 'have_a_drink',
            'in_book',
            'conditions',
            'latitude', 'longitude',
        ]

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        super(PlaceForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        place = super(PlaceForm, self).save(commit=True)
        place.owner = self.profile
        if commit:
            place.save()
            self.profile.places.add(place)
        return place


class PhoneForm(forms.ModelForm):
    class Meta:
        model = Phone
        fields = ['number', 'type']

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        super(PhoneForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        phone = super(PhoneForm, self).save(commit=False)
        phone.profile = self.profile
        if commit:
            phone.save()
        return phone
