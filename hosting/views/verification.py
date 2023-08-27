import json
from collections import OrderedDict

from django.core import serializers
from django.core.exceptions import NON_FIELD_ERRORS, PermissionDenied
from django.forms import ModelForm
from django.http import (
    HttpResponseBadRequest, HttpResponseRedirect, JsonResponse,
)
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.vary import vary_on_headers

from core.auth import PERM_SUPERVISOR, AuthMixin, AuthRole
from core.mixins import LoginRequiredMixin

from ..forms import PhoneForm, PlaceForm, ProfileForm
from ..models import LocationConfidence, Place, Profile
from .mixins import PlaceMixin


class InfoConfirmView(LoginRequiredMixin, generic.View):
    """
    Allows the current user (only) to confirm their profile and accommodation
    details as up-to-date.
    """
    http_method_names = ['post']
    template_name = 'links/confirmed.html'

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        try:
            request.user.profile.confirm_all_info()
        except Profile.DoesNotExist:
            if request.is_ajax():
                return HttpResponseBadRequest(
                    "Cannot confirm data; a profile must be created first.",
                    content_type="text/plain")
            else:
                return HttpResponseRedirect(reverse_lazy('profile_create'))
        else:
            if request.is_ajax():
                return JsonResponse({'success': 'confirmed'})
            else:
                return TemplateResponse(request, self.template_name)


class PlaceCheckView(AuthMixin, PlaceMixin, generic.View):
    """
    Allows a supervisor to confirm accommodation details of a user as up-to-date.
    The profile and place data are both validated to make sure they conform to
    the requirements from hosts and guests.
    """
    http_method_names = ['post']
    template_names = {True: '200.html', False: 'hosting/place_check_detail.html'}
    display_fair_usage_condition = True
    minimum_role = AuthRole.SUPERVISOR

    class LocationDummyForm(ModelForm):
        class Meta:
            model = Place
            fields = ['location', 'location_confidence']

        def clean(self):
            if not self.initial['location'] or self.initial['location'].empty:
                self.add_error('location', _("The geographical location on map is unknown."))
            elif self.initial['location_confidence'] < LocationConfidence.ACCEPTABLE:
                self.add_error('location', _("The geographical location on map is imprecise."))
            else:
                self.cleaned_data = {'location': self.data['location']}

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except PermissionDenied:
            if self.role == AuthRole.OWNER and self.request.user.has_perm(PERM_SUPERVISOR):
                raise PermissionDenied(
                    _(
                        "You cannot approve your own place."
                        " Ask another supervisor or an administrator to check it."
                    ), self
                )
            raise

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        place = self.get_object()
        data = [
            (ProfileForm, [place.owner]),
            (PlaceForm, [place]),
            (self.LocationDummyForm, [place]),
            (PhoneForm, place.owner.phones.filter(deleted_on__isnull=True)),
        ]
        all_forms = []
        for form_class, objects in data:
            for object_model in objects:
                object_data = serializers.serialize('json', [object_model], fields=form_class._meta.fields)
                object_data = json.loads(object_data)[0]['fields']
                all_forms.append(form_class(data=object_data, instance=object_model))

        data_correct = all([form.is_valid() for form in all_forms])  # We want all validations.
        viewresponse = {'result': data_correct}
        if not data_correct:
            viewresponse['err'] = OrderedDict()
            data_problems = set()
            for form in all_forms:
                viewresponse['err'].update({
                    self._get_field_label(form, field_name) : list(field_errs)  # noqa: E203
                    for field_name, field_errs
                    in [(k, set(err for err in v if err)) for k, v in form.errors.items()]
                    if field_name != NON_FIELD_ERRORS and len(field_errs)
                })
                data_problems.update(form.errors.get(NON_FIELD_ERRORS, []))
            if len(data_problems):
                viewresponse['err'+NON_FIELD_ERRORS] = list(data_problems)
        else:
            place.set_check_status(self.request.user)

        if request.is_ajax():
            return JsonResponse(viewresponse)
        else:
            return TemplateResponse(
                request,
                self.template_names[data_correct],
                context={'view': self, 'place': place, 'result': viewresponse}
            )

    def _get_field_label(self, form, field_name):
        if not isinstance(form, PhoneForm):
            return str(form.fields[field_name].label)
        else:
            return (
                f"{form.fields[field_name].label} {form.data['number']}"
                f" ({form.initial['country'].name or form.initial['country'].code})"
            )
