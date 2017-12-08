from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.decorators.cache import never_cache

from core.auth import OWNER

from .models import Phone, Place, Profile


class ProfileMixin(object):
    def get_object(self, queryset=None):
        return get_object_or_404(Profile, pk=self.kwargs['pk'])


class ProfileModifyMixin(object):
    def get_success_url(self, *args, **kwargs):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        if hasattr(self.object, 'profile'):
            return self.object.profile.get_edit_url()
        if type(self.object) is Profile:
            return self.object.get_edit_url()


class ProfileIsUserMixin(object):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not kwargs.get('auth_base').owner.user:
                raise Http404("Detached profile (probably a family member).")
        except AttributeError:
            pass
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if not profile.user:
            raise Http404("Detached profile (probably a family member).")
        return profile


class CreateMixin(object):
    minimum_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        if self.kwargs.get('profile_pk'):
            profile = get_object_or_404(Profile, pk=self.kwargs['profile_pk'])
            self.create_for = profile
        elif self.kwargs.get('place_pk'):
            place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
            self.create_for = place

        kwargs['auth_base'] = getattr(self, 'create_for', None)
        return super().dispatch(request, *args, **kwargs)


class PlaceMixin(object):
    def get_object(self, queryset=None):
        return get_object_or_404(Place, pk=self.kwargs['pk'])

    def get_location(self, object):
        return object.country


class PhoneMixin(object):
    def get_object(self, queryset=None):
        return get_object_or_404(Phone, pk=self.kwargs['pk'], profile=self.kwargs['profile_pk'])


class FamilyMemberMixin(object):
    def dispatch(self, request, *args, **kwargs):
        self.get_place()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if profile in self.place.family_members_cache():
            return profile
        else:
            raise Http404("Profile {} is not a family member at place {}.".format(profile.pk, self.place.pk))

    def get_place(self):
        if not hasattr(self, 'place'):
            self.place = getattr(self, 'create_for', None) or get_object_or_404(Place, pk=self.kwargs['place_pk'])
        return self.place

    @cached_property
    def other_places(self):
        return Place.objects.filter(family_members__pk=self.object.pk).exclude(pk=self.place.pk)

    def get_owner(self, object):
        return self.get_place().owner

    def get_location(self, object):
        return self.get_place().country

    def get_success_url(self, *args, **kwargs):
        return self.place.owner.get_edit_url()


class FamilyMemberAuthMixin(object):
    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if profile.user:
            raise Http404("Only the user can modify their profile.")
        return profile


class UpdateMixin(object):
    minimum_role = OWNER
    update_partial = False

    @never_cache
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object.set_check_status(
            self.request.user,
            clear_only=getattr(self, 'update_partial', False))
        return super().form_valid(form)


class DeleteMixin(object):
    minimum_role = OWNER

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
