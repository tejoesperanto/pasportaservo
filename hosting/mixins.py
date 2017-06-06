from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.views.decorators.cache import never_cache
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from .models import Profile, Place, Phone
from core.auth import ADMIN, STAFF, SUPERVISOR, OWNER, VISITOR


def get_role(request, profile):
    user = request.user
    try:
        user_profile = user.profile
    except Profile.DoesNotExist:
        return VISITOR
    if profile == user_profile:
        return OWNER
    if user.is_superuser:
        return ADMIN
    if user.is_staff:
        return STAFF
    if user_profile.is_supervisor_of(profile):
        return SUPERVISOR
    return VISITOR


class ProfileModifyMixin(object):
    def get_object(self, queryset=None):
        print("~  ProfileMixin#get_object")
        object = super().get_object(queryset)
        print("~  ProfileMixin#get_object:", object)
        return object

    def get_success_url(self, *args, **kwargs):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        if hasattr(self.object, 'profile'):
            return self.object.profile.get_edit_url()
        if type(self.object) is Profile:
            return self.object.get_edit_url()


class ProfileIsUserMixin(object):
    def dispatch(self, request, *args, **kwargs):
        print("~  ProfileIsUserMixin#dispatch")
        try:
            if not kwargs.get('auth_base').owner.user:
                raise Http404("Detached profile (probably a family member).")
        except AttributeError:
            pass
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        print("~  ProfileIsUserMixin#get_object")
        profile = super().get_object(queryset)
        print("~  ProfileIsUserMixin#get_object:", profile)
        if not profile.user:
            raise Http404("Detached profile (probably a family member).")
        return profile


class CreateMixin(object):
    minimum_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        print("~  CreateMixin#dispatch")
        if self.kwargs.get('pk'):
            profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
            self.create_for = profile
            #self.role = get_role(self.request, profile=profile)
        elif self.kwargs.get('place_pk'):
            place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
            self.create_for = place
            #self.role = get_role(self.request, profile=place.owner)

        kwargs['auth_base'] = getattr(self, 'create_for', None)
        print("~  ~  base:  ", repr(kwargs['auth_base']))
        #if self.role >= self.minimum_role:
        #    return super().dispatch(request, *args, **kwargs)
        #else:
        #    raise Http404("Not allowed to create object.")
        return super().dispatch(request, *args, **kwargs)


#class ProfileAuthMixin(object):
#    def get_object(self, queryset=None):
#        profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
#        self.role = get_role(self.request, profile=profile)
#        if self.role == VISITOR:
#            public = getattr(self, 'public_view', False)
#            if not public:
#                raise Http404("Not allowed to edit this profile.")
#            if profile.deleted:
#                raise Http404("Profile was deleted.")
#        return profile


class PlaceMixin(object):
    def get_object(self, queryset=None):
        return get_object_or_404(Place, pk=self.kwargs['pk'])

    def get_location(self, object):
        return object.country


#class PlaceAuthMixin(object):
#    minimum_role = OWNER
#
#    def get_object(self, queryset=None):
#        print("~  PlaceAuthMixin#get_object")
#        place = get_object_or_404(Place, pk=self.kwargs['pk'])
#        print("~  PlaceAuthMixin#get_object:", place)
#        self.role = get_role(self.request, profile=place.owner)
#        if self.role >= self.minimum_role:
#            return place
#        raise Http404("Not allowed to edit this place.")


class PhoneMixin(object):
    def get_object(self, queryset=None):
        return get_object_or_404(Phone, pk=self.kwargs['pk'], profile=self.kwargs['profile_pk'])


class FamilyMemberMixin(object):
    #minimum_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        self.get_place()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
            print("~  FamilyMemberMixin#get_object")
        #self.role = get_role(self.request, self.place.owner)
        #if self.role >= self.minimum_role:
        #    profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
            profile = super().get_object(queryset)
            print("~  FamilyMemberMixin#get_object:", profile)
            if profile in self.place.family_members.all():
                return profile
            else:
                raise Http404("Profile {} is not a family member at place {}.".format(profile.id, self.place.id))
        #raise Http404("You don't own this place.")

    def get_place(self):
        if not hasattr(self, 'place'):
            self.place = getattr(self, 'create_for', None) or get_object_or_404(Place, pk=self.kwargs['place_pk'])
        return self.place

    @property
    def other_places(self):
        if not hasattr(self, '_places_cache'):
            self._places_cache = Place.objects.filter(family_members__pk=self.object.pk).exclude(pk=self.place.pk)
        return self._places_cache

    def get_owner(self, object):
        return self.get_place().owner

    def get_location(self, object):
        return self.get_place().country

    def get_success_url(self, *args, **kwargs):
        return self.place.owner.get_edit_url()


class FamilyMemberAuthMixin(object):
    def get_object(self, queryset=None):
        print("~  FamilyMemberAuthMixin#get_object")
        profile = super().get_object(queryset)
        print("~  FamilyMemberAuthMixin#get_object:", profile)
        if profile.user:
            raise Http404("Only the user can modify their profile.")
        return profile


class UpdateMixin(object):
    minimum_role = OWNER

    @never_cache
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object.set_check_status(self.request.user)
        return super().form_valid(form)


class DeleteMixin(object):
    minimum_role = OWNER

    def get_object(self, queryset=None):
        if getattr(self, 'object', None) is not None:
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
