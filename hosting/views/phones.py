import re

from django.http import HttpResponseRedirect, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.vary import vary_on_headers

from core.auth import AuthMixin, AuthRole

from ..forms import PhoneCreateForm, PhoneForm
from ..models import Phone
from .mixins import (
    CreateMixin, DeleteMixin, PhoneMixin, ProfileAssociatedObjectCreateMixin,
    ProfileIsUserMixin, ProfileMixin, ProfileModifyMixin, UpdateMixin,
)


class PhoneCreateView(
        CreateMixin, AuthMixin, ProfileIsUserMixin,
        ProfileAssociatedObjectCreateMixin, ProfileModifyMixin,
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


class PhonePriorityChangeView(AuthMixin, ProfileMixin, generic.View):
    http_method_names = ['post']
    minimum_role = AuthRole.OWNER

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        profile = self.get_object()
        # This validation should be sufficient; non-existing IDs and phone IDs not
        # belonging to the profile will be filtered out by Django and not affected.
        phone_ids = re.findall(
            r'^t(\d+)$',
            '\n'.join(request.POST.getlist('onr')),
            re.MULTILINE)
        profile.set_phone_order(phone_ids)
        priorities = list(profile.get_phone_order())
        if request.is_ajax():
            return JsonResponse({'result': priorities})
        else:
            profile_url = profile.get_edit_url()
            if priorities:
                profile_url += f'#t{priorities[0]}'
            return HttpResponseRedirect(profile_url)
