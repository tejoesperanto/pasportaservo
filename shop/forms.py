from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Reservation


class ReservationForm(forms.ModelForm):
    in_book = forms.BooleanField(
        initial=False, required=False,
        label=_("I'm a host and I will appear in the book"),
        help_text=_("I can have my book at a discounted price"))

    class Meta:
        model = Reservation
        fields = ['amount', 'discount', 'support']

    def __init__(self, *args, **kwargs):
        is_in_book = kwargs.pop('is_in_book')
        self.user = kwargs.pop('user')
        self.product = kwargs.pop('product')
        super().__init__(*args, **kwargs)

        self.fields['in_book'].initial = is_in_book
        self.fields['in_book'].widget.attrs.update({
            'data-bind': "checked: inBook"})
        self.fields['amount'].widget.attrs.update({
            'class': "form-control input-lg text-center",
            'data-bind': "textInput: productAmount"})
        self.fields['discount'].widget.attrs['data-bind'] = "checked: hasTejoDiscount, cli"
        self.fields['support'].localize = True
        self.fields['support'].widget = forms.TextInput(attrs={
            'class': "form-control pull-right same-as-body",
            'style': "width: 5em; text-align: right; padding-right: calc(1em - 1px)",
            'pattern': "[0-9]{1,4},[0-9]{2}",
            'data-bind': "textInput: supportInput"})

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user, instance.product = self.user, self.product
        if commit:
            instance.save()
        return instance
