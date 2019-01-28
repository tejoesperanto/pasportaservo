import random
from hashlib import sha256

from django import template

register = template.Library()


@register.simple_tag
def random_identifier(length=None):
    try:
        length = int(length)
    except Exception:
        length = None
    if length is None or length <= 0:
        length = random.randint(16, 48)
    return ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789_')
                   for n in range(length))


@register.filter(is_safe=True)
def public_id(account):
    try:
        return sha256(str(account.pk).encode() + str(account.date_joined).encode()).hexdigest()
    except Exception:
        return ''


register.simple_tag(func=lambda *args: list(args), name='list')


register.simple_tag(func=lambda **kwargs: dict(kwargs), name='dict')


@register.filter(is_safe=True)
def are_any(iterable):
    try:
        return any(iterable)
    except (ValueError, TypeError):
        return bool(iterable)


@register.filter(is_safe=True)
def are_all(iterable):
    try:
        return all(iterable)
    except (ValueError, TypeError):
        return bool(iterable)


@register.filter(is_safe=False)
def mult(value, by):
    try:
        return value * int(by)
    except (ValueError, TypeError):
        return ''


@register.filter(is_safe=True)
@template.defaultfilters.stringfilter
def compact(value):
    """
    A template filter that removes all extra whitespace from the value it is applied to, and strips any whitespace
    at the beginning and at the end of the resulting string. Any characters that can role as whitespace (including
    new lines) are replaced by a space and collapsed.
    """
    return ' '.join(value.split())
