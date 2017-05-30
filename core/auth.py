import re

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.http import Http404
from django.conf import settings
from django.views import generic

from django_countries.fields import Country
from hosting.models import Profile, Place

from .utils import camel_case_split


PERM_SUPERVISOR = 'hosting.can_supervise'
ADMIN, STAFF, SUPERVISOR, OWNER, VISITOR, ANONYMOUS = 50, 40, 30, 20, 10, 0


class SupervisorAuthBackend(ModelBackend):

    _perm_sv_particular_re = re.compile(r'^%s\.[A-Z]{2}$' % PERM_SUPERVISOR.replace('.', '\\.'), re.I)

    def get_user_supervisor_of(self, user_obj, obj=None, code=False):
        """
        Calculate responsibilities, globally or for an optional object.
        The given object may be an iterable of countries, a single country, or a profile.
        """
        print("\tcalculating countries")
        cache_name = '_countrygroup_cache'
        if not hasattr(user_obj, cache_name):
            print("\t\t ... storing in cache %s ... " % cache_name)
            user_groups = user_obj.groups.all() if not user_obj.is_superuser else Group.objects.all()
            user_countries = frozenset(Country(g.name) for g in user_groups if len(g.name) == 2)
            setattr(user_obj, cache_name, user_countries)
        supervised = getattr(user_obj, cache_name)
        print("\tobject is", repr(obj))
        if obj is not None:
            if isinstance(obj, Country):
                countries = [obj]
                print("\t\tGot a Country,", countries)
            elif isinstance(obj, Profile):
                countries = obj.owned_places.filter(deleted=False).values_list('country', flat=True)
                print("\t\tGot a Profile,", countries)
            elif isinstance(obj, Place):
                countries = [obj.country]
                print("\t\tGot a Place,", countries)
            elif hasattr(obj, '__iter__') and not isinstance(obj, str):
                countries = obj  # assume an iterable of countries
                print("\t\tGot an iterable,", countries)
            else:
                raise ImproperlyConfigured(
                    "Supervisor check needs either a profile, a country, or a list of countries."
                )
            print("\t\trequested:", set(countries), "supervised:", set(supervised),
                  "\n\t\tresult", set(supervised) & set(countries))
            supervised = set(supervised) & set(countries)
        return supervised if code else [c.name for c in supervised]

    def is_user_supervisor_of(self, user_obj, obj=None):
        """
        Compare intersection between responsibilities and given countries.
        The given object may be an iterable of countries, a single country, or a profile.
        """
        supervised = self.get_user_supervisor_of(user_obj, obj or object(), code=True)
        return any(supervised)

    def has_perm(self, user_obj, perm, obj=None):
        """
        Verify if this user has permission (to an optional object).
        Short-circuits when resposibility is not satisfied.
        """
        print("checking permission: ", perm, " %s %s" % ("for object", repr(obj)) if obj else " for any records")
        if perm == PERM_SUPERVISOR and obj is not None:
            all_perms = self.get_all_permissions(user_obj, obj)
            allowed = any(self._perm_sv_particular_re.match(p) for p in all_perms)
        else:
            allowed = super().has_perm(user_obj, perm, obj)
        if perm == PERM_SUPERVISOR and not allowed:
            print("permission to supervise not granted")
            raise PermissionDenied
        return allowed

    def get_all_permissions(self, user_obj, obj=None):
        if obj is not None and user_obj.is_active and not user_obj.is_anonymous:
            return self.get_group_permissions(user_obj, obj)
        else:
            return super().get_all_permissions(user_obj, obj)

    def get_group_permissions(self, user_obj, obj=None):
        """
        Return a list of permission strings that this user has through their groups.
        If an object is passed in, only permissions matching this object are returned.
        """
        perms = super().get_group_permissions(user_obj, obj)
        print("\tUser's built in perms: ", perms)
        groups = set(self.get_user_supervisor_of(user_obj, code=True))
        if any(groups):
            print("\tUser's groups: ", groups)
            if obj is None:
                perms.update([PERM_SUPERVISOR])
            cache_name = '_countrygroup_perm_cache'
            if not hasattr(user_obj, cache_name):
                print("\t\t ... storing in cache %s ... " % cache_name)
                setattr(user_obj, cache_name, frozenset("%s.%s" % (PERM_SUPERVISOR, g) for g in groups))
            print("\tUser's group perms: ", set(getattr(user_obj, cache_name)))
            if obj is None:
                perms.update(getattr(user_obj, cache_name))
            else:
                groups_for_obj = set(self.get_user_supervisor_of(user_obj, obj, code=True))
                perms_for_obj = set("%s.%s" % (PERM_SUPERVISOR, g) for g in groups_for_obj)
                print("\tUser's perms for object: ", perms_for_obj)
                perms.update(getattr(user_obj, cache_name) & perms_for_obj)
        print("\tUser's all perms: ", perms)
        return perms


def get_role_in_context(request, profile=None, place=None):
    print("~  ~  PROFILE", repr(profile), "PLACE", repr(place))
    user = request.user
    if profile and user == profile.user:
        return OWNER
    if user.is_superuser:
        return ADMIN
    #Staff users is a dormant feature. Exact role to be decided.
    #Once enabled, the interaction with perms.hosting.can_supervise has to be verified.
    #if user.is_staff:
    #    return STAFF
    if user.has_perm(PERM_SUPERVISOR, place or profile or object):
        return SUPERVISOR
    return VISITOR


class AuthMixin(AccessMixin):
    minimum_role = OWNER
    allow_anonymous = False

    def get_object(self, queryset=None):
        """
        Permission check for detail, update, and delete views.
        As we need the context (the object manipulated), do the check in get_object()
        reusing the already-retrieved object, to avoid overhead and multiple trips
        to the database.
        """
        print("~  AuthMixin#get_object")
        object = super().get_object(queryset)
        print("~  AuthMixin#get_object:", object)
        return self._auth_verify(object)

    def dispatch(self, request, *args, **kwargs):
        """
        Permission check for create and general views.
        The context is determined according to the parent object, which is expected
        to be already retrieved by previous dispatch() methods, and stored in the
        auth_base keyword argument.
        """
        print("~  AuthMixin#dispatch .... ", "Create" if isinstance(self, generic.CreateView) else "Other")
        if getattr(self, 'exact_role', None) == ANONYMOUS or self.minimum_role == ANONYMOUS:
            self.allow_anonymous = True
        if not request.user.is_authenticated and not self.allow_anonymous:
            return self.handle_no_permission() # authorization implies a logged-in user
        if 'auth_base' in kwargs:
            object = kwargs['auth_base']
            self._auth_verify(object)
        elif isinstance(self, generic.CreateView):
            raise ImproperlyConfigured(
                "Creation base not found. Make sure {View}'s auth_base is accessible by "
                "AuthMixin as a dispatch kwarg.".format(View=self.__class__.__name__)
            )
        return super().dispatch(request, *args, **kwargs)

    def get_owner(self, object):
        try:
            return super().get_owner(object)
        except AttributeError:
            return object.owner if object else None

    def get_location(self, object):
        try:
            return super().get_location(object)
        except AttributeError:
            return None

    def _auth_verify(self, object):
        self.role = get_role_in_context(self.request,
                                        profile=self.get_owner(object),
                                        place=self.get_location(object))
        if getattr(self, 'exact_role', None):
            print("exact role allowed: {-", self.exact_role, "-} , current role: {-", self.role, "-}")
            if self.role == self.exact_role:
                return object
        else:
            print("minimum role allowed: {-", self.minimum_role, "-} , current role: {-", self.role, "-}")
            if self.role >= self.minimum_role:
                return object
        if settings.DEBUG:
            view_name = camel_case_split(self.__class__.__name__)
            raise PermissionDenied(
                "Not allowed to {0} this {1}.".format(view_name[-2].lower(), " ".join(view_name[0:-2]).lower())
            )
        else:
            raise Http404("Operation not allowed.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = dict(VISITOR=VISITOR, OWNER=OWNER, SUPERVISOR=SUPERVISOR, STAFF=STAFF, ADMIN=ADMIN)
        return context

