import json
from collections import OrderedDict

from django.core import serializers
from django.core.exceptions import NON_FIELD_ERRORS
from django.http import (
    HttpResponseBadRequest, HttpResponseRedirect, JsonResponse,
)
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.vary import vary_on_headers

from core.auth import SUPERVISOR, AuthMixin
from core.mixins import LoginRequiredMixin

from ..forms import PlaceForm, ProfileForm
from ..mixins import PlaceMixin
from ..models import Profile


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
    template_name = '404.html'
    minimum_role = SUPERVISOR

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        place = self.get_object()
        place_data = serializers.serialize('json', [place], fields=PlaceForm._meta.fields)
        place_data = json.loads(place_data)[0]['fields']
        owner_data = serializers.serialize('json', [place.owner], fields=ProfileForm._meta.fields)
        owner_data = json.loads(owner_data)[0]['fields']

        owner_form = ProfileForm(data=owner_data, instance=place.owner)
        place_form = PlaceForm(data=place_data, instance=place)

        data_correct = all([owner_form.is_valid(), place_form.is_valid()])  # We want both validations.
        viewresponse = {'result': data_correct}
        if not data_correct:
            viewresponse['err'] = OrderedDict()
            data_problems = set()
            for form in [owner_form, place_form]:
                viewresponse['err'].update({
                    str(form.fields[field_name].label) : list(field_errs)       # noqa: E203
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
            # Not implemented; only AJAX requests are expected.
            return TemplateResponse(request, self.template_name)
