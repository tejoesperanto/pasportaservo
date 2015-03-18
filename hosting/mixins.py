from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404

from .models import Profile, Place, Phone


class ProfileMixin(object):
    def get_success_url(self, *args, **kwargs):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        if hasattr(self.object, 'profile'):
            return self.object.profile.get_edit_url()
        if type(self.object) is Profile:
            return self.object.get_edit_url()


class ProfileAuthMixin(object):
    def get_object(self, queryset=None):
        profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
        if profile == self.request.user.profile:
            self.role = 'user'
        elif self.request.user.is_staff:
            self.role = 'admin'
        # elif profile.~places~.country in self.request.user.profile.countries:
            # self.role = 'supervizor'
        else:
            public = getattr(self, 'public_view', False)
            if not public or profile.deleted:
                raise Http404
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
        self.place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
        return super(FamilyMemberMixin, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        own_place = self.place.owner == self.request.user.profile
        if own_place or self.request.user.is_staff:
            return get_object_or_404(Profile, pk=self.kwargs['pk'])
        raise Http404

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
