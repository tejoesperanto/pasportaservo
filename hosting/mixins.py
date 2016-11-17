from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.mixins import UserPassesTestMixin

from .models import Profile, Place, Phone
from .models import ADMIN, STAFF, SUPERVISOR, OWNER, VISITOR


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


class StaffMixin(UserPassesTestMixin):
    def test_func(self):
        return lambda: self.request.user.is_staff


class ProfileMixin(object):
    def get_success_url(self, *args, **kwargs):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        if hasattr(self.object, 'profile'):
            return self.object.profile.get_edit_url()
        if type(self.object) is Profile:
            return self.object.get_edit_url()


class CreateMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if self.kwargs.get('pk'):
            profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
            self.role = get_role(self.request, profile=profile)
        elif self.kwargs.get('place_pk'):
            place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
            self.role = get_role(self.request, profile=place.owner)

        if self.role >= OWNER:
            return super().dispatch(request, *args, **kwargs)
        else:
            raise Http404("Not allowed to create object.")


class ProfileAuthMixin(object):
    def get_object(self, queryset=None):
        profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
        self.role = get_role(self.request, profile=profile)
        if self.role == VISITOR:
            public = getattr(self, 'public_view', False)
            if not public:
                raise Http404("Not allowed to edit this profile.")
            if profile.deleted:
                raise Http404("Profile was deleted.")
        return profile


class PlaceAuthMixin(object):
    def get_object(self, queryset=None):
        place = get_object_or_404(Place, pk=self.kwargs['pk'])
        self.role = get_role(self.request, profile=place.owner)
        if self.role >= OWNER:
            return place
        raise Http404("Not allowed to edit this place.")


class PhoneAuthMixin(object):
    def get_object(self, queryset=None):
        number = get_object_or_404(Phone,
            number__icontains=self.kwargs['num'].replace('-', ' '))
        self.role = get_role(self.request, profile=number.profile)
        if self.role >= OWNER:
            return number
        raise Http404("Not allowed to edit this phone number.")


class FamilyMemberMixin(object):
    def dispatch(self, request, *args, **kwargs):
        self.place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        self.role = get_role(self.request, self.place.owner)
        if self.role >= OWNER:
            profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
            if profile in self.place.family_members.all():
                return profile
            else:
                raise Http404("Profile " + str(profile.id) + " is not a family member at place " + str(self.place.id) + ".")
        raise Http404("You don't own this place.")

    def get_success_url(self, *args, **kwargs):
        return self.place.owner.get_edit_url()


class FamilyMemberAuthMixin(object):
    def get_object(self, queryset=None):
        profile = super().get_object(queryset)
        if profile.user:
            raise Http404("Only the user can modify their profile.")
        return profile


class DeleteMixin(object):
    def delete(self, request, *args, **kwargs):
        """
        Set the flag 'deleted' to True on the object
        and then redirects to the success URL
        """
        self.object = self.get_object()
        self.object.deleted = True
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())
