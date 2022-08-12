from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field

from ..models import Phone
from ..validators import client_side_validated


@client_side_validated
class PhoneForm(forms.ModelForm):
    class Meta:
        model = Phone
        fields = ['number', 'type', 'country', 'comments']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'profile'):
            self.profile = self.instance.profile
        self.helper = FormHelper(self)
        self.helper[0:2].wrap_together(Div, css_class='row')
        self.fields['number'].widget.input_type = 'tel'
        self.helper['number'].wrap(Field, wrapper_class='col-xxs-12 col-xs-7')
        self.helper['type'].wrap(Field, wrapper_class='col-xxs-12 col-xs-5')

    def clean(self):
        """
        Checks if the number and the profile are unique together.
        """
        cleaned_data = super().clean()
        if 'number' in cleaned_data:
            data = cleaned_data['number'].as_e164
            if self.instance.number and data == self.instance.number.as_e164:
                phones = Phone.all_objects.none()
            else:
                # Check is done for object creation (self.instance.number == None)
                # and for object update (self.instance.number != data)
                phones = Phone.all_objects.filter(number=data, profile=self.profile)
            assert len(phones) <= 1, "Something is very wrong with the DB."
            if len(phones) == 1:
                self.existing_phone = phones[0]
                if not phones[0].deleted:
                    self.add_error('number', _("You already have this telephone number."))
        return cleaned_data

    def save(self, commit=True):
        phone = super().save(commit=False)
        if hasattr(self, 'existing_phone') and self.existing_phone.deleted:
            # Just overwrite the existing deleted phone object with new data
            # (i.e., type and comments), because the user did not remember
            # deleting this phone number.
            for field in filter(lambda f: f != 'number', self._meta.fields):
                setattr(self.existing_phone, field, getattr(phone, field))
            phone = self.existing_phone
            # Clear the deletion timestamp.
            phone.deleted_on = None
            # Clear the verification user id and timestamp.
            phone.set_check_status(self.profile.user, clear_only=True, commit=False)
            # Mark the original phone object being updated as deleted.
            if self.instance.pk:
                self.instance.deleted_on = timezone.now()
                self.instance.save(update_fields=['deleted_on'])
        if commit:
            phone.save()
        return phone
    save.alters_data = True


class PhoneCreateForm(PhoneForm):
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        phone = super().save(commit=False)
        phone.profile = self.profile
        if commit:
            phone.save()
        return phone
    save.alters_data = True
