import logging
import re
import types
import warnings
from enum import Enum
from functools import total_ordering
from typing import Literal, Union

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import Http404, HttpResponseNotAllowed
from django.utils.functional import SimpleLazyObject
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.views import generic

from django_countries.fields import Country

from hosting.models import Place, Profile

from .utils import camel_case_split, join_lazy

auth_log = logging.getLogger('PasportaServo.auth')


PERM_SUPERVISOR = 'hosting.can_supervise'


@total_ordering
class AuthRole(Enum):
    """
    An enumeration of authorization roles. Users will receive one of these roles
    on the hosting-related views, according to the context.
    """
    ANONYMOUS = 0
    VISITOR = 10
    PLACE_GUEST = VISITOR, ...
    PLACE_FAMILYMEMBER = VISITOR, ...
    OWNER = 20
    SUPERVISOR = 30
    STAFF = 40
    ADMIN = 50

    parent: Union['AuthRole', None]
    do_not_call_in_templates: Literal[True]

    def __new__(cls, value, subvalue=None):
        obj = object.__new__(cls)
        obj._value_ = (len(cls) + 1, subvalue) if subvalue is not None else value
        # Late resolution since we want the parent to point to the actual enumeration's member.
        obj.parent = SimpleLazyObject(lambda: cls(value)) if subvalue is not None else None
        return obj

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            if not other.parent:
                return (self.value if not self.parent else self.parent.value) > other.value
            else:
                raise NotImplementedError(
                    f'Comparison not supported for subtype of {other.parent}'
                    ' as right-hand side')
        return NotImplemented

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            if not other.parent:
                return (self.value if not self.parent else self.parent.value) >= other.value
            else:
                raise NotImplementedError(
                    f'Comparison not supported for subtype of {other.parent}'
                    ' as right-hand side')
        return NotImplemented

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            if self is other:
                return True
            if self.parent and other.parent:
                raise NotImplementedError(
                    'Comparison not suported between subtypes')
            lhs_value = self.value if not self.parent else self.parent.value
            rhs_value = other.value if not other.parent else other.parent.value
            return lhs_value == rhs_value
        return NotImplemented

    __hash__ = Enum.__hash__

    def __repr__(self):
        self_repr = f'{self.__class__.__name__}.{self.name}'
        if self.parent:
            return f'<{self_repr} :: {self.parent.__class__.__name__}.{self.parent.name}>'
        else:
            return f'<{self_repr}: {self.value}>'

    def __str__(self):
        if self.parent:
            return f'{self.parent.name} ({self.name})'
        else:
            return self.name

AuthRole.do_not_call_in_templates = True  # noqa:E305


class SupervisorAuthBackend(ModelBackend):

    _perm_sv_particular_re = re.compile(r'^%s\.[A-Z]{2}$' % PERM_SUPERVISOR.replace('.', '\\.'), re.I)

    def user_can_authenticate(self, user):
        """
        Allow all logins. The actual policy will be handled by the AuthenticationForm's
        method confirm_login_allowed().
        """
        return True

    def get_user_supervisor_of(self, user_obj, obj=None, code=False):
        """
        Calculate responsibilities, globally or for an optional object.
        The given object may be an iterable of countries, a single country, or a profile.
        """
        auth_log.debug("\tcalculating countries")
        cache_name = '_countrygroup_cache'
        if not hasattr(user_obj, cache_name):
            auth_log.debug("\t\t ... storing in cache %s ... ", cache_name)
            user_groups = user_obj.groups.all() if not user_obj.is_superuser else Group.objects.all()
            user_countries = frozenset(Country(g.name) for g in user_groups if len(g.name) == 2)
            setattr(user_obj, cache_name, user_countries)
        supervised = getattr(user_obj, cache_name)
        if auth_log.getEffectiveLevel() == logging.DEBUG:
            auth_log.debug("\tobject is %s", repr(obj))
        if obj is not None:
            if isinstance(obj, Country):
                countries = [obj]
                auth_log.debug("\t\tGot a Country, %s", countries)
            elif isinstance(obj, Profile):
                countries = obj.owned_places.filter(deleted=False).values_list('country', flat=True)
                auth_log.debug("\t\tGot a Profile, %s", countries)
            elif isinstance(obj, Place):
                countries = [obj.country]
                auth_log.debug("\t\tGot a Place, %s", countries)
            elif hasattr(obj, '__iter__') and not isinstance(obj, str):
                countries = obj  # Assume an iterable of countries.
                auth_log.debug("\t\tGot an iterable, %s", countries)
            else:
                raise ImproperlyConfigured(
                    "Supervisor check needs either a profile, a country, or a list of countries."
                )
            if auth_log.getEffectiveLevel() == logging.DEBUG:
                auth_log.debug(
                    "\t\trequested: %s supervised: %s\n\t\tresult: %s",
                    set(countries), set(supervised), set(supervised) & set(countries))
            supervised = set(supervised) & set(countries)
        return supervised if code else [c.name for c in supervised]

    def is_user_supervisor_of(self, user_obj, obj=None):
        """
        Compare intersection between responsibilities and given countries.
        The given object may be an iterable of countries, a single country, or a profile.
        """
        supervised = self.get_user_supervisor_of(
            user_obj, obj if obj is not None else object(), code=True)
        return any(supervised)

    def has_perm(self, user_obj, perm, obj=None):
        """
        Verify if this user has permission (to an optional object).
        Short-circuits when resposibility is not satisfied.
        """
        if auth_log.getEffectiveLevel() == logging.DEBUG:
            auth_log.debug(
                "checking permission:  %s [ %s ] for %s",
                perm, user_obj, "%s %s" % ("object", repr(obj)) if obj else "any records")
        if perm == PERM_SUPERVISOR and obj is not None:
            all_perms = self.get_all_permissions(user_obj, obj)
            allowed = any(self._perm_sv_particular_re.match(p) for p in all_perms)
        else:
            allowed = super().has_perm(user_obj, perm, obj)
        if perm == PERM_SUPERVISOR and not allowed:
            auth_log.debug("permission to supervise not granted")
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
        auth_log.debug("\tUser's built in perms:  %s", perms)
        groups = set(self.get_user_supervisor_of(user_obj, code=True))
        if any(groups):
            auth_log.debug("\tUser's groups:  %s", groups)
            if obj is None:
                perms.update([PERM_SUPERVISOR])
            cache_name = '_countrygroup_perm_cache'
            if not hasattr(user_obj, cache_name):
                auth_log.debug("\t\t ... storing in cache %s ... ", cache_name)
                setattr(
                    user_obj, cache_name,
                    frozenset("%s.%s" % (PERM_SUPERVISOR, g) for g in groups))
            if auth_log.getEffectiveLevel() == logging.DEBUG:
                auth_log.debug("\tUser's group perms:  %s", set(getattr(user_obj, cache_name)))
            if obj is None:
                perms.update(getattr(user_obj, cache_name))
            else:
                groups_for_obj = set(self.get_user_supervisor_of(user_obj, obj, code=True))
                perms_for_obj = set("%s.%s" % (PERM_SUPERVISOR, g) for g in groups_for_obj)
                auth_log.debug("\tUser's perms for object:  %s", perms_for_obj)
                perms.update(getattr(user_obj, cache_name) & perms_for_obj)
        auth_log.debug("\tUser's all perms:  %s", perms)
        return perms


def get_role_in_context(request, profile=None, place=None, no_obj_context=False):
    user = request.user
    context = place or profile or object
    if profile and user.pk == profile.user_id:
        return AuthRole.OWNER
    if user.is_superuser:
        return AuthRole.ADMIN
    # Staff users is a dormant feature. Exact role to be decided.
    # Once enabled, the interaction with perms.hosting.can_supervise has to be verified.
    # if user.is_staff:
    #     return AuthRole.STAFF
    if user.has_perm(PERM_SUPERVISOR, None if no_obj_context else context):
        return AuthRole.SUPERVISOR
    return AuthRole.VISITOR


class AuthMixin(AccessMixin):
    minimum_role = AuthRole.OWNER
    exact_role: AuthRole | tuple[AuthRole]
    allow_anonymous = False
    redirect_field_name = settings.REDIRECT_FIELD_NAME
    display_permission_denied = True
    permission_denied_message = _("Only the supervisors of {this_country} can access this page")

    class MisconfigurationWarning(UserWarning):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dispatch_func = self.dispatch

        def _dispatch_wrapper(wrapped_self, wrapped_request, *wrapped_args, **wrapped_kwargs):
            result = dispatch_func(wrapped_request, *wrapped_args, **wrapped_kwargs)
            if not hasattr(wrapped_self, 'role') and not isinstance(result, HttpResponseNotAllowed):
                warnings.warn(
                    "AuthMixin is present on the view {} but no authorization check was performed. "
                    "Check super() calls and order of inheritance.".format(self.__class__.__name__),
                    AuthMixin.MisconfigurationWarning, stacklevel=2)
            return result

        self.dispatch = types.MethodType(_dispatch_wrapper, self)

    def get_object(self, queryset=None):
        """
        Permission check for detail, update, and delete views.
        As we need the context (the object manipulated), do the check in get_object()
        reusing the already-retrieved object, to avoid overhead and multiple trips
        to the database.
        """
        object = super().get_object(queryset)
        return self._auth_verify(object)

    def dispatch(self, request, *args, **kwargs):
        """
        Permission check for create and general views.
        The context is determined according to the parent object, which is expected
        to be already retrieved by previous dispatch() methods, and stored in the
        auth_base keyword argument.
        """
        if (getattr(self, 'exact_role', None) == AuthRole.ANONYMOUS
                or self.minimum_role == AuthRole.ANONYMOUS):
            self.allow_anonymous = True
        if not request.user.is_authenticated and not self.allow_anonymous:
            self.role = AuthRole.VISITOR
            return self.handle_no_permission()  # Authorization implies a logged-in user.
        if 'auth_base' in kwargs:
            object = kwargs['auth_base']
            self._auth_verify(object, context_omitted=object is None)
        elif isinstance(self, generic.CreateView):
            raise ImproperlyConfigured(
                "Creation base not found. Make sure {}'s auth_base is accessible by "
                "AuthMixin as a dispatch kwarg.".format(self.__class__.__name__)
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

    def _auth_verify(self, object, context_omitted=False):
        self.role = get_role_in_context(self.request,
                                        profile=self.get_owner(object),
                                        place=self.get_location(object),
                                        no_obj_context=context_omitted)
        if getattr(self, 'exact_role', None):
            roles_allowed = (self.exact_role if isinstance(self.exact_role, tuple)
                             else (self.exact_role, ))
            auth_log.info(
                "exact role allowed: {- %s -} , current role: {- %s -}",
                " or ".join(str(r) for r in roles_allowed), self.role)
            if self.role in roles_allowed:
                return object
        else:
            auth_log.info(
                "minimum role allowed: {- %s -} , current role: {- %s -}",
                self.minimum_role, self.role)
            if self.role >= self.minimum_role:
                return object
        if settings.DEBUG:  # pragma: no cover
            view_name = camel_case_split(self.__class__.__name__)
            raise PermissionDenied(
                "Not allowed to {action} this {obj}.".format(
                    action=view_name[-2].lower(), obj=" ".join(view_name[0:-2]).lower()
                ), self
            )
        elif self.display_permission_denied and self.request.user.has_perm(PERM_SUPERVISOR):
            raise PermissionDenied(
                self.get_permission_denied_message(object, context_omitted),
                self)
        else:
            raise Http404("Operation not allowed.")

    def get_permission_denied_message(self, object, context_omitted=False):
        if not context_omitted:
            countries = [self.get_location(object)]
            if not countries[0]:
                countries = self.get_owner(object).owned_places.filter(
                    deleted=False
                ).values_list('country', flat=True).distinct()
            elif not countries[0].name:
                countries = []
        else:
            countries = None
        if not countries:
            return _("Only administrators can access this page")
        return format_lazy(
            self.permission_denied_message,
            this_country=join_lazy(", ", countries, lambda item: str(Country(item).name))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = AuthRole
        return context
