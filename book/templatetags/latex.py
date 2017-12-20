from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.filter
def escape_latex(value):
    return value.replace(
        '&', '\&').replace(
        '%', '\%').replace(
        '_', '\_').replace(
        '$', '\$').replace(
        '#', '\#').replace(
        '{', '\{').replace(
        '}', '\}').replace(
        # '\\', '\\textbackslash ').replace(
        '~', '\\textasciitilde ').replace(
        '^', '\\textasciicircum ')


@register.filter
def cmd(value, command):
    """Latex command: \command{value}"""
    return '\{}{{{}}}'.format(command, value)


@register.filter
def ctx(value, arg):
    """Latex context: {\context value}"""
    contexts = ''.join('\{}'.format(context) for context in arg.split(','))
    return '{{{} {}}}'.format(contexts, value)


@register.filter
def bracket(value):
    return '({})'.format(value)


@register.filter
def color(value, arg='gray'):
    return r'\textcolor{{{}}}{{{}}}'.format(arg, value)


@register.filter
def full_name(profile):
    """Returns \name{first}{last} or \eastname{first}{last}"""
    cmd = 'eastname' if profile.names_inversed else 'name'
    return '\{0}{{{1}}}{{{2}}}'.format(
        cmd,
        escape_latex(profile.first_name),
        escape_latex(profile.last_name)
    )


@register.filter
def supervisors(country):
    group = Group.objects.get(name=country)
    return sorted(user.profile for user in group.user_set.all())


@register.filter
def map_for(country):
    group = Group.objects.get(name=country)
    return sorted(user.profile for user in group.user_set.all())
