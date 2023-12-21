import random
from hashlib import sha256
from typing import Any, Optional, cast
from urllib.parse import quote as urlquote, urlencode, urlparse

from django import template
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.http import HttpRequest
from django.utils import translation
from django.utils.safestring import SafeData, mark_safe

from core.utils import sanitize_next

register = template.Library()


@register.simple_tag
def random_identifier(length: Any = None):
    try:
        length = int(length)
    except Exception:
        length = None
    if length is None or length <= 0:
        length = random.randint(16, 48)
    return ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789_')
                   for _ in range(length))


@register.filter(is_safe=True)
def public_id(account):
    try:
        return sha256(str(account.pk).encode() + str(account.date_joined).encode()).hexdigest()
    except Exception:
        return ''


register.simple_tag(func=lambda *args: list(args), name='list')


register.simple_tag(func=lambda **kwargs: dict(kwargs), name='dict')


@register.simple_tag
def dict_insert(d: dict, key: Any, value: Any):
    d[key] = value
    return ''


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
def split(value: Any, by: Optional[str] = None):
    """
    A template filter to split objects (commonly, strings) by the given argument. A missing argument will split the
    object by any whitespace; if the object cannot be split, it will be wrapped in a list. Strings marked as "safe"
    by Django will still have their parts correctly marked in the resulting list.
    If the argument is of the form 'separator~number', the resulting chunks will have a maximum length of `number`;
    this means that to use a tilde as separator, it must be doubled: '~~'. The chunking will also un-mark the parts
    as "safe" because it might cut HTML tags into several (not-safe-anymore) pieces; Use only for plain text.
    """
    length = None
    try:
        if by == 'NEWLINE':
            by = '\n'
        if by and isinstance(by, str) and '~' in by:
            by, length = by.rsplit('~', maxsplit=1)
            try:
                length = abs(int(length))
            except ValueError:
                length = None
        parts = value.split(by)
    except (ValueError, TypeError, AttributeError):
        parts = [value]

    if isinstance(value, SafeData):
        parts = [mark_safe(part) for part in parts]
    if length:
        parts = [[part[i:i+length] for i in range(0, len(part), length)] if part else [part] for part in parts]
        return [chunk for part_chunks in parts for chunk in part_chunks]
    else:
        return parts


@register.filter(is_safe=False)
def mult(value, by):
    try:
        return value * int(by)
    except (ValueError, TypeError):
        return ''


@register.filter(is_safe=True)
@template.defaultfilters.stringfilter
def compact(value: str):
    """
    A template filter that removes all extra whitespace from the value it is applied to, and strips any whitespace
    at the beginning and at the end of the resulting string. Any characters that can role as whitespace (including
    new lines) are replaced by a space and collapsed.
    """
    return ' '.join(value.split())


@register.simple_tag
def get_system_language():
    """
    A template tag that retrieves the currently active system language without reliance on the i18n context
    processor. The result can optionally be saved in a template variable.
    """
    return translation.get_language()


@register.simple_tag(takes_context=True)
def get_user_language(context):
    """
    A template tag that retrieves the user's current language preference without reliance on the LocaleMiddleware.
    """
    if 'request' not in context:
        return settings.LANGUAGE_CODE  # Same fallback as for `get_language_from_request`.
    return translation.get_language_from_request(context['request'])


@register.filter
def content_page_language(content_page: FlatPage, prefix_url: Optional[str] = None):
    """
    A template filter to extract the language code from a localized content page (flat page). Each such page
    should have a URL in the form: /PREFIX/LANG-CODE/local-slug/
    """
    if prefix_url and content_page.url.startswith(prefix_url):
        url = cast(str, content_page.url)[len(prefix_url):].lstrip('/')
        return url.split('/', maxsplit=1)[0]
    else:
        return cast(str, content_page.url).split('/')[2]


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


@register.simple_tag(name='previous', takes_context=True)
def previous_link(context, default=''):
    """
    A template tag used to provide the properly verified redirection target for going back to the previously
    visited page.
      - default: provides a default value to output in case the redirection target is empty or unsafe.
    """
    url_param_value = ''
    if 'request' in context:
        referrer_url = context['request'].META.get('HTTP_REFERER', '')
        url_param_value = sanitize_next(context['request'], url=referrer_url)
    return urlparse(url_param_value).path or default
