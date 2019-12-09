import random
from hashlib import sha256
from urllib.parse import urlencode

from django import template
from django.conf import settings
from django.http import HttpRequest
from django.utils.http import urlquote

from core.utils import sanitize_next

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


@register.simple_tag(name='next', takes_context=True)
def next_link(
        context,
        proceed_to, proceed_to_anchor=None, proceed_to_anchor_id=None,
        url_only=False, default=''):
    """
    A template tag used to provide the properly encoded redirection target parameter for URLs. The target can be
    specified directly, or via the tokens 'this page' (meaning, the current page's URL will be used) or 'next page'
    (meaning, the value from current page's redirection parameter will be used).  In the latter case, the target
    value is verified prior to use; an unsafe value is ignored. The additional parameters:
      - url_only: causes the tag to output only the calculated target's URL, without encoding for a Query String.
      - default:  provides a default value to output in case the indicated redirection target is empty or unsafe.
    """
    if str(proceed_to).startswith('#'):
        proceed_to_anchor_id, proceed_to_anchor, proceed_to = proceed_to_anchor, proceed_to, 'this page'
    if isinstance(context, HttpRequest):
        context = {'request': context}
    url_param = ''

    if proceed_to == "this page":
        if 'request' in context:
            url_param = context['request'].get_full_path()
    elif proceed_to == "next page":
        if 'request' in context:
            url_param = sanitize_next(context['request'])
    else:
        url_param = proceed_to

    url_param_value = ''.join([
        str(url_param),
        str(proceed_to_anchor) if proceed_to_anchor else '',
        str(proceed_to_anchor_id) if proceed_to_anchor and proceed_to_anchor_id else '',
    ]) if url_param else default
    if not url_only and url_param_value:
        return urlencode(
            {settings.REDIRECT_FIELD_NAME: url_param_value},
            quote_via=lambda v, *args: urlquote(v, safe='')
        )
    else:
        return url_param_value or ''
