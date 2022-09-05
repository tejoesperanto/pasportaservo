import logging
import re

from django import template
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import AnonymousUser
from django.template.defaultfilters import stringfilter
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.auth import PERM_SUPERVISOR, auth_log

from ..models import Profile
from ..utils import value_without_invalid_marker

register = template.Library()


def _convert_profile_to_user(profile_obj):
    if isinstance(profile_obj, Profile):
        return profile_obj.user or AnonymousUser()
    else:
        return profile_obj


@register.filter
def is_supervisor(user_or_profile):
    user = _convert_profile_to_user(user_or_profile)
    if auth_log.getEffectiveLevel() == logging.DEBUG:
        auth_log.debug(
            "* checking if supervising... [ %s %s]",
            user, "<~ '%s' " % user_or_profile if user != user_or_profile else "")
    return user.has_perm(PERM_SUPERVISOR)


@register.filter
def is_supervisor_of(user_or_profile, profile_or_countries):
    user = _convert_profile_to_user(user_or_profile)
    if auth_log.getEffectiveLevel() == logging.DEBUG:
        auth_log.debug(
            "* checking if object is supervised... [ %s %s] [ %s ]",
            user, "<~ '%s' " % user_or_profile if user != user_or_profile else "",
            repr(profile_or_countries))
    if isinstance(profile_or_countries, int):
        # Assumed pk of a profile.
        try:
            profile_or_countries = Profile.objects.get(pk=profile_or_countries)
        except Profile.DoesNotExist:
            # For consistency, superusers are treated as supervisors of non-
            # existing profiles, as they are assumed to have all permissions.
            return False if not user.is_superuser else True
    elif isinstance(profile_or_countries, str):
        # Assumed a list of country codes.
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
    if auth_log.getEffectiveLevel() == logging.DEBUG:
        auth_log.debug(
            "* searching supervised objects... [ %s %s]",
            user, "<~ '%s' " % user_or_profile if user != user_or_profile else "")
    for backend in auth.get_backends():
        try:
            return sorted(backend.get_user_supervisor_of(user))
        except Exception:
            pass
    return []


@register.simple_tag(takes_context=True)
def get_approver(context, model_instance):
    # This tag is provided for enabling transparent caching of User and Profile objects
    # referenced in the `checked_by` property of TrackingModel instances.  Without such
    # caching, each instance causes a new DB query even when the approving User is just
    # the same...
    if not model_instance or not model_instance.checked_by_id:
        return None
    if 'user' in context:
        default_cache = {context['user'].pk: context['user']}
    else:
        default_cache = {}
    cache = context['view'].__dict__.setdefault('approvers_cache', default_cache)
    if model_instance.checked_by_id not in cache:
        cache[model_instance.checked_by_id] = model_instance.checked_by
    return cache[model_instance.checked_by_id]


@register.filter
def format_pronoun(profile, tag=''):
    tag = tag.lstrip('<').rstrip('>')
    return mark_safe(" ".join(
        format_html("<{tag}>{part}</{tag}>", tag=tag, part=part.capitalize()) if index % 2 else part
        for index, part in enumerate(profile.get_pronoun_parts(), start=1)
    ))


@register.filter
def get_pronoun(profile):
    if profile and profile.pronoun:
        if profile.pronoun == profile.Pronouns.ANY:
            return profile.Pronouns.NEUTRAL.label
        else:
            return profile.get_pronoun_parts()[0]
    else:
        return Profile.Pronouns.NEUTRAL.label


@register.filter
def avatar_dimension(profile, size_percent=100):
    if profile and profile.avatar_exists():
        if profile.avatar.width < profile.avatar.height:
            dimension = ["width"]
            aspect = "tall"
        else:
            dimension = ["height"]
            aspect = "wide"
    else:
        dimension = ["width", "height"]
        aspect = "square"
    return mark_safe(" ".join(
        ["{attr}=\"{s:.2f}%\"".format(attr=attr, s=float(size_percent)) for attr in dimension]
        + ["data-{aspect}".format(aspect=aspect)]
    ))


@register.filter
def icon(model_instance, field=''):
    obj = model_instance if not field else model_instance._meta.get_field(field)
    return getattr(obj, 'icon', '')


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
                          r'c\^|g\^|h\^|j\^|s\^|u\^|u~|\^c|\^g|\^h|\^j|\^s|\^u|~u',
                          re.IGNORECASE)
