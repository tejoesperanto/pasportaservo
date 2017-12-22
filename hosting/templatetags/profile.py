import logging
import re

from django import template
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import AnonymousUser
from django.template.defaultfilters import stringfilter

from core.auth import PERM_SUPERVISOR

from ..models import Profile
from ..utils import value_without_invalid_marker

register = template.Library()

auth_log = logging.getLogger('PasportaServo.auth')


def _convert_profile_to_user(profile_obj):
    if isinstance(profile_obj, Profile):
        return profile_obj.user or AnonymousUser()
    else:
        return profile_obj


@register.filter
def is_supervisor(user_or_profile):
    user = _convert_profile_to_user(user_or_profile)
    auth_log.debug(
        "* checking if supervising... [ %s %s]",
        user, "<~ '%s' " % user_or_profile if user != user_or_profile else "")
    return user.has_perm(PERM_SUPERVISOR)


@register.filter
def is_supervisor_of(user_or_profile, profile_or_countries):
    user = _convert_profile_to_user(user_or_profile)
    auth_log.debug(
        "* checking if object is supervised... [ %s %s] [ %s ]",
        user, "<~ '%s' " % user_or_profile if user != user_or_profile else "",
        repr(profile_or_countries))
    if isinstance(profile_or_countries, int):
        try:
            profile_or_countries = Profile.objects.get(pk=profile_or_countries)
        except Profile.DoesNotExist:
            return False
    elif isinstance(profile_or_countries, str):
        profile_or_countries = profile_or_countries.split(" ")

    # supervisor = False
    # for backend in auth.get_backends():
    #     try:
    #         supervisor = backend.is_user_supervisor_of(user, profile_or_countries)
    #     except AttributeError as e:
    #         pass
    #     except:
    #         supervisor = False
    #     else:
    #         break
    # return supervisor
    return user.has_perm(PERM_SUPERVISOR, profile_or_countries)


@register.filter
def supervisor_of(user_or_profile):
    user = _convert_profile_to_user(user_or_profile)
    auth_log.debug(
        "* searching supervised objects... [ %s %s]",
        user, "<~ '%s' " % user_or_profile if user != user_or_profile else "")
    for backend in auth.get_backends():
        try:
            return sorted(backend.get_user_supervisor_of(user))
        except Exception:
            pass
    return ("",)


@register.filter(is_safe=True)
@stringfilter
def is_invalid(value):
    return str(value).startswith(settings.INVALID_PREFIX)


@register.filter(is_safe=True)
@stringfilter
def clear_invalid(value):
    return value_without_invalid_marker(value)


@register.filter(is_safe=True)
@stringfilter
def is_esperanto_surrogate(value):
    return re_esperanto.search(value)


re_esperanto = re.compile(r'cx|gx|hx|jx|sx|ux|ch|gh|hh|jh|sh|'
                          r'c\^|g\^|h\^|j\^|s\^|u\^|u~|\^c|\^g|\^h|\^j|\^s|\^u|~u')
