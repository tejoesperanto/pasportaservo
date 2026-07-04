from typing import TYPE_CHECKING, cast

from django import template
from django.contrib.auth.models import Group

from hosting.models import PasportaServoUser, Phone, Profile

from .latex import escape_latex

if TYPE_CHECKING:
    from hosting.models import FullProfile

register = template.Library()


@register.filter
def full_name(profile: Profile):
    r"""
    Returns `\name{first}{last}` or `\eastname{first}{last}`
    """
    cmd = 'eastname' if profile.names_inversed else 'name'
    return r'\{0}{{{1}}}{{{2}}}'.format(
        cmd,
        escape_latex(profile.first_name),
        escape_latex(profile.last_name)
    )


@register.filter
def latex_icon(object):
    icon = ''
    if isinstance(object, Phone):
        match object.type:
            case Phone.PhoneType.MOBILE:
                icon = r"\raisebox{-0.10em}{\faMobile*}"
            case Phone.PhoneType.FAX:
                icon = r"\raisebox{-0.08em}{\faFax}"
            case _:
                icon = r"\raisebox{-0.15em}{\faPhone*}"
    return icon


@register.simple_tag
def get_public_phone_numbers(profile: 'FullProfile'):
    return (
        profile.phones
        .filter(deleted=False, visibility__visible_in_book=True)
        .select_related(None)
    )


@register.filter
def supervisors(country: str):
    group = Group.objects.get(name=country)
    return sorted(
        user.profile
        for group_member in group.user_set.all()
        if (user := cast(PasportaServoUser, group_member)).is_active
        and hasattr(user, 'profile')
        and user.profile.deleted_on is None
        and user.profile.death_date is None
    )
