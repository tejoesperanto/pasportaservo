from django.utils.translation import ugettext_lazy as _
from django.views import generic

from core.auth import AuthMixin

from ..forms import PhoneCreateForm, PhoneForm
from ..models import Phone
from .mixins import (
    CreateMixin, DeleteMixin, PhoneMixin, ProfileAssociatedObjectCreateMixin,
    ProfileIsUserMixin, ProfileModifyMixin, UpdateMixin,
)


class PhoneCreateView(
        CreateMixin, AuthMixin, ProfileIsUserMixin, ProfileAssociatedObjectCreateMixin, ProfileModifyMixin,
        generic.CreateView):
    model = Phone
    form_class = PhoneCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.create_for
        return kwargs

    def get_confirmation_message(self):
        return _("A new phone was added.")


class PhoneUpdateView(
        UpdateMixin, AuthMixin, PhoneMixin, ProfileModifyMixin,
        generic.UpdateView):
    form_class = PhoneForm
    display_fair_usage_condition = True


class PhoneDeleteView(
        DeleteMixin, AuthMixin, PhoneMixin, ProfileModifyMixin,
        generic.DeleteView):
    pass
