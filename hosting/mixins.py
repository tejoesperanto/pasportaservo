from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.core.exceptions import PermissionDenied

from .models import Profile, Place, Phone


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
            user_profile = getattr(self.request.user, 'profile', None)
            creation_allowed = self.request.user.is_staff or (user_profile and profile == user_profile)
        elif self.kwargs.get('place_pk'):
            place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
            user_profile = getattr(self.request.user, 'profile', None)
            creation_allowed = self.request.user.is_staff or (user_profile and place.owner == user_profile)
        
        if creation_allowed:
            return super(CreateMixin, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied("Not allowed to create object.")


class ProfileAuthMixin(object):
    def get_object(self, queryset=None):
        profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
        user_profile = getattr(self.request.user, 'profile', None)
        if user_profile and profile == user_profile:
            self.role = 'user'
        elif self.request.user.is_staff:
            self.role = 'admin'
        # elif profile.~places~.country in self.request.user.profile.countries:
            # self.role = 'supervizor'
        else:
            public = getattr(self, 'public_view', False)
            if not public:
                raise PermissionDenied("Not allowed to edit this profile.")
            if profile.deleted:
                raise Http404("Profile was deleted.")
            self.role = 'visitor'
        return profile


class PlaceAuthMixin(object):
    def get_object(self, queryset=None):
        pk = self.kwargs['pk']
        if self.request.user.is_staff:
            return get_object_or_404(Place, pk=pk)
        return get_object_or_404(Place, pk=pk, owner=self.request.user.profile)


class PhoneAuthMixin(object):
    def get_object(self, queryset=None):
        number = self.kwargs['num'].replace('-', ' ')
        user = self.request.user
        if user.is_staff:
            return get_object_or_404(Phone, number__icontains=number)
        return get_object_or_404(Phone,
                                 number__icontains=number,
                                 profile=user.profile)


class FamilyMemberMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            self.place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
        else:
            self.place = get_object_or_404(Place, pk=self.kwargs['place_pk'], owner=self.request.user.profile)
        return super(FamilyMemberMixin, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        own_place = self.place.owner == self.request.user.profile
        if own_place or self.request.user.is_staff:
            return get_object_or_404(Profile, pk=self.kwargs['pk'])
        raise PermissionDenied("You don't own this place.")

    def get_success_url(self, *args, **kwargs):
        return self.place.owner.get_edit_url()


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
