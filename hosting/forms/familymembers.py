from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Profile
from ..validators import client_side_validated


@client_side_validated
class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['title', 'first_name', 'last_name', 'names_inversed', 'birth_date']
        error_messages = {
            'birth_date': {'max_value': _("A family member cannot be future-born (even if planned).")},
        }

    def __init__(self, *args, **kwargs):
        self.place = kwargs.pop('place')
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['inputmode'] = 'latin-name'
        self.fields['last_name'].widget.attrs['inputmode'] = 'latin-name'
        if not self.place_has_family_members():
            self.fields['first_name'].help_text = _(
                "Leave empty if you only want to indicate that other people are present in the house.")
        self.fields['birth_date'].widget.attrs['pattern'] = (
            '[1-2][0-9]{3}-((0[1-9])|(1[0-2]))-((0[1-9])|([12][0-9])|(3[0-1]))')
        self.fields['birth_date'].widget.attrs['data-date-end-date'] = '0d'
        self.fields['birth_date'].widget.attrs['placeholder'] = 'jjjj-mm-tt'

    def place_has_family_members(self):
        return len(self.place.family_members_cache()) != 0 and not self.place.family_is_anonymous

    def clean(self):
        """
        Verifies that first name and last name convey some information together.
        """
        cleaned_data = super().clean()
        if 'first_name' in cleaned_data and 'last_name' in cleaned_data and self.place_has_family_members():
            if not "".join([cleaned_data['first_name'], cleaned_data['last_name']]):
                raise forms.ValidationError(_("The name cannot be empty, "
                                              "at least first name or last name are required."))
        return cleaned_data


class FamilyMemberCreateForm(FamilyMemberForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, **kwargs):
        family_member = super().save()
        self.place.family_members.add(family_member)
        return family_member
    save.alters_data = True
