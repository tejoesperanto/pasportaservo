import json
from collections import OrderedDict
from typing import Any, Iterable, Optional

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.exceptions import NON_FIELD_ERRORS, PermissionDenied
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import (
    Http404, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse,
)
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.vary import vary_on_headers

from core import PasportaServoHttpRequest
from core.auth import PERM_SUPERVISOR, AuthMixin, AuthRole
from core.mixins import LoginRequiredMixin
from core.utils import request_asks_for_json, sanitize_next

from ..forms import PhoneForm, PlaceForm, ProfileForm
from ..models import LocationConfidence, Place, Profile, TrackingModel
from .mixins import PlaceMixin

APPROVABLE_CATEGORIES = {
    model.get_model_qualifier(): model
    for model in apps.get_models()
    if issubclass(model, TrackingModel)
    and all([not model._meta.abstract, not model._meta.proxy])
}


class InfoConfirmView(LoginRequiredMixin, generic.View):
    """
    Allows the current user (only) to confirm their profile and accommodation
    details as up-to-date.
    """
    http_method_names = ['post']
    template_name = 'links/confirmed.html'

    @vary_on_headers('X-Requested-With', 'Accept')
    def post(self, request: PasportaServoHttpRequest, *args, **kwargs):
        try:
            request.user.profile.confirm_all_info()
        except Profile.DoesNotExist:
            if request_asks_for_json(request):
                return HttpResponseBadRequest(
                    "Cannot confirm data; a profile must be created first.",
                    content_type="text/plain")
            else:
                return HttpResponseRedirect(reverse_lazy('profile_create'))
        else:
            if request_asks_for_json(request):
                return JsonResponse({'success': 'confirmed'})
            else:
                return TemplateResponse(request, self.template_name)


class InfoStaffUnconfirmView(AuthMixin[TrackingModel], generic.TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'hosting/model_uncheck.html'
    minimum_role = AuthRole.SUPERVISOR
    category: str = ''

    def dispatch(self, request, *args, **kwargs):
        current_model = APPROVABLE_CATEGORIES.get(self.category)
        if not current_model:
            raise Http404(f"Model category '{self.category}' is not supported.")
        # Make type checker happy by assigning only a non-None value.
        self.current_model = current_model
        try:
            self.object = (
                current_model.all_objects
                .select_related('checked_by')
                .get(pk=self.kwargs['pk'])
            )
        except current_model.DoesNotExist:
            self.object = None  # type: ignore
        kwargs['auth_base'] = self.object
        return super().dispatch(request, *args, **kwargs)

    def _object_access_verify(self, request: PasportaServoHttpRequest):
        if self.object is None:
            error = Http404(
                f"No {self.current_model._meta.object_name} matches"
                f" the given ID '{self.kwargs['pk']}'."
            )
            if settings.DEBUG:  # pragma: no cover
                from pasportaservo.views import custom_page_not_found_view
                return custom_page_not_found_view(request, error)
            else:
                raise error
        if self.object.checked_by != request.user and not request.user.is_superuser:
            error = PermissionDenied(
                _("You can revert only your own previous approval."), self
            )
            if settings.DEBUG:  # pragma: no cover
                from pasportaservo.views import custom_permission_denied_view
                return custom_permission_denied_view(request, error)
            else:
                raise error

    def get(self, request: PasportaServoHttpRequest, *args, **kwargs):
        if error_response := self._object_access_verify(request):
            return error_response
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        context['object_type'] = self.object._meta.verbose_name
        return context

    @vary_on_headers('X-Requested-With', 'Accept')
    def post(self, request: PasportaServoHttpRequest, *args, **kwargs):
        if error_response := self._object_access_verify(request):
            return error_response
        self.object.checked_on = None
        self.object.save(update_fields=['checked_on'])
        if request.needs_json:
            return JsonResponse({
                'success': 'unconfirmed',
                'status_url': reverse_lazy(
                    f'staff_{self.category}_check_status',
                    kwargs={'pk': self.object.pk}
                ),
            })
        else:
            redirect_to = sanitize_next(request)
            if not redirect_to:
                redirect_to = self.object.owner.get_edit_url()
                if not isinstance(self.object, Profile):
                    redirect_to += f'#{self.object.get_model_anchor()}{self.object.pk}'
            return HttpResponseRedirect(redirect_to)


class PlaceCheckView(AuthMixin[Place], PlaceMixin, generic.View):
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

    def get_object(self, queryset: Optional[QuerySet[Place]] = None) -> Place:
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

    @vary_on_headers('X-Requested-With', 'Accept')
    def post(self, request: PasportaServoHttpRequest, *args, **kwargs):
        place = self.get_object()
        data: list[tuple[type[ModelForm], Iterable[TrackingModel]]] = [
            (ProfileForm, [place.owner]),
            (PlaceForm, [place]),
            (self.LocationDummyForm, [place]),
            (PhoneForm, place.owner.phones.filter(deleted_on__isnull=True)),
        ]
        all_forms: list[ModelForm] = []
        for form_class, objects in data:
            for object_model in objects:
                object_data = serializers.serialize(
                    'json', [object_model], fields=form_class._meta.fields)
                object_data = json.loads(object_data)[0]['fields']
                all_forms.append(form_class(data=object_data, instance=object_model))

        data_correct = all([form.is_valid() for form in all_forms])  # We want all validations.
        viewresponse: dict[str, Any] = {'result': data_correct}
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

        if request.needs_json:
            return JsonResponse(viewresponse)
        else:
            return TemplateResponse(
                request,
                self.template_names[data_correct],
                context={'view': self, 'place': place, 'result': viewresponse}
            )

    def _get_field_label(self, form: ModelForm, field_name: str) -> str:
        if not isinstance(form, PhoneForm):
            return str(form.fields[field_name].label)
        else:
            return (
                f"{form.fields[field_name].label} {form.data['number']}"
                f" ({form.initial['country'].name or form.initial['country'].code})"
            )


class InfoStaffCheckStatusDisplayView(AuthMixin[TrackingModel], generic.TemplateView):
    template_name = 'hosting/snippets/checked.html'
    minimum_role = AuthRole.SUPERVISOR
    category: str = ''

    def dispatch(self, request, *args, **kwargs):
        current_model = APPROVABLE_CATEGORIES.get(self.category)
        if not current_model:
            raise Http404(f"Model category '{self.category}' is not supported.")
        self.current_model = current_model
        kwargs['auth_base'] = None  # Just verify that the user is a supervisor.
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            self.object = (
                self.current_model.all_objects
                .select_related('checked_by')
                .get(pk=self.kwargs['pk'])
            )
        except self.current_model.DoesNotExist:
            error = Http404(
                f"No {self.current_model._meta.object_name} matches"
                f" the given ID '{self.kwargs['pk']}'."
            )
            if settings.DEBUG:  # pragma: no cover
                from pasportaservo.views import custom_page_not_found_view
                return custom_page_not_found_view(request, error)
            else:
                raise error
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context
