from typing import Any, cast

from django import template
from django.contrib.auth.models import Group

from hosting.models import PasportaServoUser, Profile

register = template.Library()


@register.filter
def escape_latex(value: str):
    return (
        value
        .replace('&', '\\&')
        .replace('%', '\\%')
        .replace('_', '\\_')
        .replace('$', '\\$')
        .replace('#', '\\#')
        .replace('{', '\\{')
        .replace('}', '\\}')
        # .replace('\\', '\\textbackslash ')
        .replace('~', '\\textasciitilde ')
        .replace('^', '\\textasciicircum ')
    )


@register.filter
def cmd(value: Any, command: str):
    r"""Latex command: \command{value}"""
    return rf'\{command}{{{value}}}'


@register.filter
def ctx(value: Any, arg: str):
    r"""Latex context: {\context value}"""
    contexts = ''.join(rf'\{context}' for context in arg.split(','))
    return f'{{{contexts} {value}}}'


@register.filter
def bracket(value: Any):
    return f'({value})'


@register.filter
def color(value: Any, arg: str = 'gray'):
    return rf'\textcolor{{{arg}}}{{{value}}}'


@register.filter
def full_name(profile: Profile):
    r"""Returns \name{first}{last} or \eastname{first}{last}"""
    cmd = 'eastname' if profile.names_inversed else 'name'
    return r'\{0}{{{1}}}{{{2}}}'.format(
        cmd,
        escape_latex(profile.first_name),
        escape_latex(profile.last_name)
    )


@register.filter
def supervisors(country: str):
    group = Group.objects.get(name=country)
    return sorted(
        cast(PasportaServoUser, user).profile
        for user in group.user_set.all()
    )


@register.filter
def map_for(country: str):
    group = Group.objects.get(name=country)
    return sorted(
        cast(PasportaServoUser, user).profile
        for user in group.user_set.all()
    )
