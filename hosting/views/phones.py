from django.views import generic

from core.auth import AuthMixin

from ..forms import PhoneCreateForm, PhoneForm
from ..models import Phone
from .mixins import (
    CreateMixin, DeleteMixin, PhoneMixin,
    ProfileIsUserMixin, ProfileModifyMixin, UpdateMixin,
)


class PhoneCreateView(
        CreateMixin, AuthMixin, ProfileIsUserMixin, ProfileModifyMixin,
        generic.CreateView):
    model = Phone
    form_class = PhoneCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.create_for
        return kwargs


class PhoneUpdateView(
        UpdateMixin, AuthMixin, PhoneMixin, ProfileModifyMixin,
        generic.UpdateView):
    form_class = PhoneForm


class PhoneDeleteView(
        DeleteMixin, AuthMixin, PhoneMixin, ProfileModifyMixin,
        generic.DeleteView):
    pass
