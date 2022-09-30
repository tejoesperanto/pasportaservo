from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache

from core.auth import AuthRole
from core.templatetags.utils import next_link
from core.utils import sanitize_next

from ..models import FamilyMember, LocationConfidence, Phone, Place, Profile


class ProfileMixin(object):
    model = Profile

    def get_object(self, queryset=None):
        try:
            current_user_profile_pk = (
                self.request.user_has_profile and self.request.user.profile.pk
            )
        except Profile.DoesNotExist:
            current_user_profile_pk = None
        finally:
            # When the profile-related View needs to show data of the current user, we already have
            # the Profile object in `request.user.profile` and do not need to re-query the database.
            if str(current_user_profile_pk) == str(self.kwargs['pk']):
                profile = self.request.user.profile
            else:
                where_from = queryset if queryset is not None else self.get_queryset()
                profile = get_object_or_404(where_from, pk=self.kwargs['pk'])
        return profile

    def get_queryset(self):
        try:
            return super().get_queryset()
        except AttributeError:
            return self.model._default_manager.all()


class ProfileModifyMixin(object):
    url_anchors = {Place: 'p', Phone: 't'}

    def get_success_url(self, *args, **kwargs):
        redirect_to = sanitize_next(self.request)
        if redirect_to:
            return redirect_to

        success_url, success_url_anchor = None, None
        if hasattr(self.object, 'profile'):
            success_url = self.object.profile.get_edit_url()
            success_url_anchor = self.url_anchors.get(self.model)
        if type(self.object) is Profile:
            success_url = self.object.get_edit_url()
            success_url_anchor = getattr(self, 'success_with_anchor', None)
        if success_url_anchor:
            return f'{success_url}#{success_url_anchor}{self.object.pk}'
        else:
            return success_url


class ProfileIsUserMixin(object):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not kwargs.get('auth_base').owner.user_id:
                raise Http404("Detached profile (probably a family member).")
        except AttributeError:
            pass
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if not profile.user_id:
            raise Http404("Detached profile (probably a family member).")
        return profile


class CreateMixin(object):
    minimum_role = AuthRole.OWNER

    def dispatch(self, request, *args, **kwargs):
        if self.kwargs.get('profile_pk'):
            profile = get_object_or_404(Profile, pk=self.kwargs['profile_pk'])
            self.create_for = profile
        elif self.kwargs.get('place_pk'):
            place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
            self.create_for = place

        kwargs['auth_base'] = getattr(self, 'create_for', None)
        return super().dispatch(request, *args, **kwargs)


class ProfileAssociatedObjectCreateMixin(object):
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.role == AuthRole.OWNER:
            url = ''.join((
                reverse('profile_settings',
                        kwargs={'pk': self.create_for.pk, 'slug': self.create_for.autoslug}),
                '#ppv', str(self.object.visibility.pk),
            ))
            msg_affirm = self.get_confirmation_message()
            msg_remind = _(
                "<a href=\"{url}\">Don't forget to choose</a> where it should be displayed."
            )
            messages.info(
                self.request, extra_tags='eminent',
                message=format_html("{}&ensp;{}", msg_affirm, format_html(msg_remind, url=url))
            )
        return response


class PlaceMixin(object):
    model = Place

    def get_object(self, queryset=None):
        where_from = queryset if queryset is not None else self.get_queryset()
        return get_object_or_404(where_from, pk=self.kwargs['pk'])

    def get_location(self, object):
        return object.country

    def get_queryset(self):
        try:
            return super().get_queryset()
        except AttributeError:
            return self.model._default_manager.all()


class PlaceModifyMixin(object):
    def form_valid(self, form):
        response = super().form_valid(form)
        if '_gotomap' in self.request.POST or form.confidence < LocationConfidence.ACCEPTABLE:
            map_url = reverse('place_location_update', kwargs={'pk': self.object.pk})
            redirect_to = sanitize_next(self.request)
            return HttpResponseRedirect(
                ('{}' if not redirect_to else '{}?{}').format(
                    map_url, next_link(self.request, redirect_to)
                )
            )
        return response


class PhoneMixin(object):
    model = Phone

    def get_object(self, queryset=None):
        return get_object_or_404(Phone, pk=self.kwargs['pk'], profile=self.kwargs['profile_pk'])


class FamilyMemberMixin(object):
    model = FamilyMember

    def dispatch(self, request, *args, **kwargs):
        self.get_place()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if profile in self.place.family_members_cache():
            profile.owner = self.place.owner
            return profile
        else:
            raise Http404(f"Profile {profile.pk} is not a family member at place {self.place.pk}.")

    def get_place(self):
        if not hasattr(self, 'place'):
            self.place = (
                getattr(self, 'create_for', None)
                or get_object_or_404(Place, pk=self.kwargs['place_pk'])
            )
        return self.place

    @cached_property
    def other_places(self):
        return Place.objects.filter(family_members__pk=self.object.pk).exclude(pk=self.place.pk)

    def get_owner(self, object):
        return self.get_place().owner

    def get_location(self, object):
        return self.get_place().country

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.object
        return context

    def get_success_url(self, *args, **kwargs):
        redirect_to = sanitize_next(self.request)
        if redirect_to:
            return redirect_to
        return self.place.owner.get_edit_url()


class FamilyMemberAuthMixin(object):
    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if profile.user_id:
            raise Http404("Only the user can modify their profile.")
        return profile


class UpdateMixin(object):
    minimum_role = AuthRole.OWNER
    update_partial = False

    @never_cache
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object.set_check_status(
            self.request.user,
            clear_only=(
                getattr(self, 'update_partial', False)
                or ('_save-only' in self.request.POST)
            ),
            commit=False)
        return super().form_valid(form)


class DeleteMixin(object):
    minimum_role = AuthRole.OWNER

    def get_object(self, queryset=None):
        if getattr(self, 'object', None) is not None:
            # In some use-cases, get_object will be called several times prior to deletion.
            # Avoid multiple trips to the database for those cases.
            return self.object
        return super().get_object(queryset)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.deleted:
            if hasattr(self, 'get_failure_url'):
                return HttpResponseRedirect(self.get_failure_url())
            else:
                return HttpResponseRedirect(self.get_success_url())
        else:
            return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if getattr(self, 'object', None) is None:
            self.object = self.get_object()
        if not self.object.deleted:
            self.object.deleted_on = timezone.now()
            self.object.save()
        return HttpResponseRedirect(self.get_success_url())
