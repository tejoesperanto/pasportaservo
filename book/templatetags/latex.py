from typing import Any

from django import template

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
    r"""
    Latex command: `\command{value}`
    """
    return rf'\{command}{{{value}}}'


@register.filter
def ctx(value: Any, arg: str):
    r"""
    Latex context: `{\context value}`
    """
    contexts = ''.join(rf'\{context}' for context in arg.split(','))
    return f'{{{contexts} {value}}}'


@register.filter
def bracket(value: Any):
    return f'({value})'


@register.filter
def color(value: Any, arg: str = 'gray'):
    return rf'\textcolor{{{arg}}}{{{value}}}'
