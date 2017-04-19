from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import keep_lazy_text
from .utils import format_lazy
from django.utils import timezone

from .models import Profile, Place, Phone
from core.auth import ADMIN, STAFF, SUPERVISOR, OWNER, VISITOR

from django_countries.fields import Country


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


class SupervisorRequiredMixin(UserPassesTestMixin):
    raise_exception = True
    permission_denied_message = _("Only the supervisors of {this_country} can access this page")

    def test_func(self):
        if self.request.user.is_staff:
            return True
        try:
            return self.request.user.profile.is_supervisor_of(countries=[self.country])
        except AttributeError:
            return self.request.user.profile.is_supervisor_of(self.user.profile)
        except Profile.DoesNotExist:
            return False

    def get_permission_denied_message(self):
        try:
            countries = [self.country]
        except AttributeError:
            countries = set(self.user.profile.owned_places.filter(
                available=True, deleted=False).values_list('country', flat=True))
            if not countries:
                return _("Only administrators can access this page")
        to_string = lambda item: str(Country(item).name)
        join_lazy = keep_lazy_text(lambda items: ", ".join(map(to_string, items)))
        return format_lazy(self.permission_denied_message, this_country=join_lazy(countries))


class ProfileMixin(object):
    def get_success_url(self, *args, **kwargs):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        if hasattr(self.object, 'profile'):
            return self.object.profile.get_edit_url()
        if type(self.object) is Profile:
            return self.object.get_edit_url()


class CreateMixin(object):
    minimum_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        if self.kwargs.get('pk'):
            profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
            self.role = get_role(self.request, profile=profile)
        elif self.kwargs.get('place_pk'):
            place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
            self.role = get_role(self.request, profile=place.owner)

        if self.role >= self.minimum_role:
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
    minimum_role = OWNER

    def get_object(self, queryset=None):
        place = get_object_or_404(Place, pk=self.kwargs['pk'])
        self.role = get_role(self.request, profile=place.owner)
        if self.role >= self.minimum_role:
            return place
        raise Http404("Not allowed to edit this place.")


class PhoneAuthMixin(object):
    minimum_role = OWNER

    def get_object(self, queryset=None):
        number = get_object_or_404(Phone,
            pk=self.kwargs['pk'],
            profile=self.kwargs['profile_pk'])
        self.role = get_role(self.request, profile=number.profile)
        if self.role >= self.minimum_role:
            return number
        raise Http404("Not allowed to edit this phone number.")


class FamilyMemberMixin(object):
    minimum_role = OWNER

    def dispatch(self, request, *args, **kwargs):
        self.place = get_object_or_404(Place, pk=self.kwargs['place_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        self.role = get_role(self.request, self.place.owner)
        if self.role >= self.minimum_role:
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
        self.object = self.get_object()
        self.object.deleted_on = timezone.now()
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())
