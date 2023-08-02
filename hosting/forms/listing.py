from django import forms
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from crispy_forms.bootstrap import PrependedText
from crispy_forms.helper import FormHelper

from ..widgets import ExpandedMultipleChoice


class SearchForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_class = 'col-xs-12 col-sm-3'
        self.helper.field_class = 'col-xs-12 col-sm-9'
        self.helper.wrapper_class = 'form-group-sm'
        # Do not render the CSRF Middleware token hidden input tag.
        self.helper.disable_csrf = True

        self.fields['owner__first_name'].label = _("First name")
        self.fields['owner__last_name'].label = _("Last name")
        self.fields['max_guest'].widget.attrs['min'] = 0
        self.fields['max_guest'].label = _("At least this many")
        self.helper['max_guest'].wrap(
            PrependedText,
            format_lazy('<span class="addon-fw-3">{text}</span>', text=_("guests")),
            wrapper_class=self.helper.wrapper_class)
        self.fields['max_night'].widget.attrs['min'] = 0
        self.fields['max_night'].label = (
            format_lazy('<span class="sr-only">{text}</span>', text=_("At least this many"))
        )
        self.helper['max_night'].wrap(
            PrependedText,
            format_lazy('<span class="addon-fw-3">{text}</span>', text=_("nights")),
            wrapper_class=self.helper.wrapper_class)
        self.fields['contact_before'].widget.attrs['min'] = 1
        self.fields['contact_before'].label = _("Available within")
        self.helper['contact_before'].wrap(
            PrependedText,
            format_lazy('<span class="addon-fw-3">{text}</span>', text=_("days")),
            wrapper_class=self.helper.wrapper_class)

        self.fields['available'].initial = True
        self.fields['available'].label = _("Place to sleep")
        for bool_field in ('available', 'tour_guide', 'have_a_drink'):
            self.fields[bool_field].extra_label = self.fields[bool_field].label
            self.fields[bool_field].label = _("Yes")

        self.helper['conditions'].wrap(
            ExpandedMultipleChoice,
            wrapper_class=self.helper.wrapper_class,
            collapsed=True,
            option_hover_css_classes={'true': "btn-success", 'false': "btn-danger"})

    def clean(self):
        cleaned_data = super().clean()
        # When a boolean search form field is unchecked, it means
        # "do not filter by this field".
        for field in ('available', 'tour_guide', 'have_a_drink'):
            if field in cleaned_data and not cleaned_data[field]:
                cleaned_data[field] = None
        return cleaned_data
