import logging
from copy import copy
from itertools import chain

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch
from django.db.models.functions import Trunc
from django.forms import modelformset_factory
from django.http import Http404, HttpResponseRedirect, JsonResponse, QueryDict
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.vary import vary_on_headers

from braces.views import FormInvalidMessageMixin

from core.auth import PERM_SUPERVISOR, AuthMixin, AuthRole
from core.mixins import LoginRequiredMixin

from ..forms import (
    PreferenceOptinsForm, ProfileCreateForm, ProfileEmailUpdateForm,
    ProfileForm, VisibilityForm, VisibilityFormSetBase,
)
from ..models import Profile, VisibilitySettings
from .mixins import (
    DeleteMixin, ProfileIsUserMixin, ProfileMixin,
    ProfileModifyMixin, UpdateMixin,
)

User = get_user_model()


class ProfileCreateView(
        AuthMixin, ProfileModifyMixin, FormInvalidMessageMixin,
        generic.CreateView):
    model = Profile
    form_class = ProfileCreateForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")
    exact_role = AuthRole.OWNER

    def dispatch(self, request, *args, **kwargs):
        try:
            # Redirect to profile edit page if user is logged in & profile already exists.
            assert not request.user.is_anonymous
            profile = Profile.get_basic_data(request, user=request.user)
            self.role = AuthRole.OWNER
            return HttpResponseRedirect(profile.get_edit_url(), status=301)
        except Profile.DoesNotExist:
            # Cache the result for the reverse related descriptor, to spare further DB queries.
            setattr(request.user, request.user._meta.get_field('profile').get_cache_name(), None)
            # Make up a dummy profile temporarily linked to the current user,
            # to ensure a correct authorization check.
            kwargs['auth_base'] = Profile(user=copy(request.user))
            return super().dispatch(request, *args, **kwargs)
        except AssertionError:
            self.role = AuthRole.ANONYMOUS
            # Redirect to registration page when user is not authenticated.
            return HttpResponseRedirect(reverse_lazy('register'), status=303)

    def get_form(self, form_class=ProfileCreateForm):
        return form_class(user=self.request.user, **self.get_form_kwargs())


class ProfileUpdateView(
        UpdateMixin, AuthMixin, ProfileIsUserMixin, ProfileMixin, ProfileModifyMixin, FormInvalidMessageMixin,
        generic.UpdateView):
    form_class = ProfileForm
    form_invalid_message = _("The data is not saved yet! Note the specified errors.")
    display_fair_usage_condition = True


class ProfileDeleteView(
        DeleteMixin, AuthMixin, ProfileIsUserMixin, ProfileMixin,
        generic.DeleteView):
    form_class = ProfileForm
    success_url = reverse_lazy('logout')
    display_fair_usage_condition = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['places'] = self.object.owned_places.filter(deleted=False)
        return context

    def get_success_url(self):
        # Administrators will be redirected to the deleted profile's page.
        if self.role >= AuthRole.SUPERVISOR:
            return self.object.get_absolute_url()
        return self.success_url

    def get_failure_url(self):
        return reverse_lazy('profile_settings', kwargs={
            'pk': self.object.pk, 'slug': self.object.autoslug})

    def delete(self, request, *args, **kwargs):
        """
        Set the flag 'deleted' to True on the profile and some associated objects,
        deactivate the linked user,
        and then redirect to the success URL.
        """
        now = timezone.now()
        self.object = self.get_object()
        if not self.object.deleted:
            for place in self.object.owned_places.filter(deleted=False):
                place.deleted_on = now
                place.save()
                place.family_members.filter(
                    deleted=False, user_id__isnull=True
                ).update(deleted_on=now)
            self.object.phones.filter(deleted=False).update(deleted_on=now)
            self.object.user.is_active = False
            self.object.user.save()
        if self.role == AuthRole.OWNER:
            messages.success(request, _("Farewell !"))
        return super().delete(request, *args, **kwargs)


class ProfileRestoreView(
        AuthMixin, ProfileIsUserMixin, ProfileMixin, ProfileModifyMixin,
        generic.DetailView):
    template_name = 'hosting/profile_confirm_restore.html'
    display_fair_usage_condition = True
    exact_role = AuthRole.ADMIN

    def get_permission_denied_message(self, *args, **kwargs):
        return _("Only administrators can access this page")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.deleted:
            context['linked_objects'] = (p for p in chain(self.linked_places, self.linked_phones))
        return context

    @property
    def deletion_timestamp(self):
        return self.object.deleted_on.replace(second=0, microsecond=0)

    def _truncate_delete_field(self):
        return Trunc('deleted_on', kind='minute')

    def _annotated_objects(self, qs):
        return qs.annotate(
            deleted_when=self._truncate_delete_field()
        ).filter(
            deleted_when=self.deletion_timestamp
        )

    @cached_property
    def linked_places(self):
        return self._annotated_objects(self.object.owned_places)

    @cached_property
    def linked_phones(self):
        return self._annotated_objects(self.object.phones)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.deleted:
            return self.get(request, *args, **kwargs)
        with transaction.atomic():
            [qs.update(deleted_on=None) for qs in [
                self._annotated_objects(Profile.all_objects)
                    .filter(
                        pk__in=self.linked_places.values_list('family_members', flat=True),
                        user_id__isnull=True),
                self.linked_places,
                self.linked_phones,
                Profile.all_objects.filter(pk=self.object.pk),
            ]]
            User.objects.filter(pk=self.object.user_id).update(is_active=True)
        return HttpResponseRedirect(self.object.get_edit_url())


class ProfileRedirectView(LoginRequiredMixin, generic.RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if kwargs.get('pk'):
            try:
                profile = Profile.get_basic_data(pk=kwargs['pk'])
            except Profile.DoesNotExist:
                raise Http404("No profile with the given id exists.")
            if profile.user_id:
                return profile.get_absolute_url()
            else:
                raise Http404("Detached profile (probably a family member).")

        try:
            profile = Profile.get_basic_data(self.request, user=self.request.user)
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')
        else:
            return profile.get_edit_url()


class ProfileDetailView(
        AuthMixin, ProfileIsUserMixin, ProfileMixin,
        generic.DetailView):
    display_fair_usage_condition = True
    public_view = True
    minimum_role = AuthRole.VISITOR

    def get_queryset(self):
        qs = super().get_queryset().select_related('user', 'email_visibility')
        if self.request.user.has_perm(PERM_SUPERVISOR):
            qs = qs.select_related('checked_by', 'checked_by__profile')
        return qs

    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if profile.deleted:
            if self.role == AuthRole.VISITOR and not self.request.user.has_perm(PERM_SUPERVISOR):
                raise Http404("Profile was deleted.")
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        display_places = self.object.owned_places.filter(deleted=False)
        if self.public_view:
            display_places = display_places.filter(visibility__visible_online_public=True)
        else:
            family_members = Prefetch(
                'family_members',
                Profile.all_objects.order_by('birth_date').select_related('user'))
            display_places = display_places.prefetch_related(family_members)
        if self.request.user.has_perm(PERM_SUPERVISOR):
            display_places = (display_places
                              .select_related('checked_by', 'checked_by__profile')
                              .defer('checked_by__profile__description'))
        context['places'] = display_places.select_related('visibility')

        display_phones = self.object.phones.filter(deleted=False)
        context['phones'] = display_phones
        context['phones_public'] = (display_phones
                                    .filter(visibility__visible_online_public=True)
                                    .select_related(None))

        return context


class ProfileEditView(ProfileDetailView):
    template_name = 'hosting/profile_edit.html'
    public_view = False
    minimum_role = AuthRole.OWNER


class ProfileSettingsView(ProfileDetailView):
    template_name = 'hosting/settings.html'
    minimum_role = AuthRole.OWNER

    @property
    def profile_email_help_text(self):
        return Profile._meta.get_field('email').help_text

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['account'] = self.object.user
        context['privacy_matrix'] = ProfilePrivacyUpdateView.VisibilityFormSet(
            profile=self.object,
            read_only=(self.role > AuthRole.OWNER and self.role < AuthRole.ADMIN),
            prefix=ProfilePrivacyUpdateView.VISIBILITY_FORMSET_PREFIX)
        context['optinouts_form'] = PreferenceOptinsForm(instance=self.object.pref)
        context['optinouts_form'].helper.disable_csrf = True
        return context


class ProfileSettingsRedirectView(LoginRequiredMixin, generic.RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        try:
            profile = Profile.get_basic_data(self.request, user=self.request.user)
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')
        else:
            return reverse_lazy('profile_settings', kwargs={
                'pk': profile.pk, 'slug': profile.autoslug})


class ProfileEmailUpdateView(
        AuthMixin, ProfileIsUserMixin, ProfileMixin, ProfileModifyMixin,
        generic.UpdateView):
    template_name = 'hosting/profile-email_form.html'
    form_class = ProfileEmailUpdateForm
    display_fair_usage_condition = True
    success_with_anchor = 'e'
    minimum_role = AuthRole.OWNER


class ProfilePrivacyUpdateView(AuthMixin, ProfileMixin, generic.View):
    http_method_names = ['post']
    exact_role = (AuthRole.OWNER, AuthRole.ADMIN)

    VisibilityFormSet = modelformset_factory(
        VisibilitySettings,
        form=VisibilityForm, formset=VisibilityFormSetBase, extra=0)
    VISIBILITY_FORMSET_PREFIX = 'publish'

    def get_permission_denied_message(self, *args, **kwargs):
        return _("Only the user themselves can access this page")

    @vary_on_headers('HTTP_X_REQUESTED_WITH')
    def post(self, request, *args, **kwargs):
        profile = self.get_object()
        data = QueryDict(request.body)

        publish_formset = self.VisibilityFormSet(
            profile=profile, data=data, prefix=self.VISIBILITY_FORMSET_PREFIX)
        matrix_data_correct = publish_formset.is_valid()
        if matrix_data_correct:
            publish_formset.save()
        else:
            for index, err in enumerate(publish_formset.errors):
                err['_pk'] = publish_formset[index].instance.pk
                if err:
                    err['_obj'] = repr(publish_formset[index].instance)
            logging.getLogger('PasportaServo.{module_}.{class_}'.format(
                module_=__name__, class_=self.__class__.__name__
            )).error(f'{publish_formset.non_form_errors()!r}, {publish_formset.errors}')

        optins_form = PreferenceOptinsForm(data=data, instance=profile.pref)
        optins_data_correct = optins_form.is_valid()
        if optins_data_correct:
            optins_form.save()

        if request.is_ajax():
            return JsonResponse({'result': matrix_data_correct and optins_data_correct})
        else:
            if not matrix_data_correct:
                raise ValueError(
                    "Unexpected visibility configuration. "
                    f"Ref {publish_formset.non_form_errors() + publish_formset.errors!r}"
                )
            if not optins_data_correct:
                raise ValueError(
                    "Opt-in/out preference could not be set. "
                    f"Ref {optins_form.errors!r}"
                )
            return HttpResponseRedirect('{}#pR'.format(profile.get_edit_url()))
