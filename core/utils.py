import hashlib
import locale
import operator
import re
from decimal import Decimal, localcontext as local_decimal_context
from functools import reduce
from typing import Any, Iterable, Literal, Optional, Sequence, Tuple, overload

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.core.mail.backends.base import BaseEmailBackend
from django.http import HttpRequest
from django.utils.functional import (
    SimpleLazyObject, keep_lazy_text, lazy, new_method_proxy,
)
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe

import requests
from anymail.message import AnymailMessage
from packvers import version


def getattr_(obj, path):
    return reduce(getattr, path.split('.') if isinstance(path, str) else path, obj)


def split(value: str) -> list[str]:
    """
    Improvement of "".split(), with support of apostrophe.
    """
    return re.split(r'\W+', value)


def camel_case_split(identifier: str) -> list[str]:
    """
    Converts AStringInCamelCase to a list of separate words.
    """
    # stackoverflow.com/a/29920015/1019109 -by- stackoverflow.com/u/1157100/200-success
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return [m.group(0) for m in matches]


def _lazy_joiner(sep, items, item_to_string=str):
    return str(sep).join(map(item_to_string, items))

join_lazy = lazy(_lazy_joiner, str)  # noqa:E305

mark_safe_lazy = keep_lazy_text(mark_safe)


# Monkey-patch Django's SimpleLazyObject to support integers and operations on them.
setattr(SimpleLazyObject, '__int__', new_method_proxy(int))
setattr(SimpleLazyObject, '__add__', new_method_proxy(operator.add))
setattr(SimpleLazyObject, '__mul__', new_method_proxy(operator.mul))


def version_to_numeric_repr(version_string: str, precision: Optional[int] = None) -> Decimal:
    """
    Converts a version string to a numeric representation. For each component of the
    version five digits are reserved and the first component is the most significant
    part of the result.
    If the version does not follow the PEP 440 specification, the given string is
    converted to a fraction by using the ASCII values of the characters and their
    positions, ensuring that the result is unique and can be compared numerically.
    """
    version_object = version.parse(version_string)
    with local_decimal_context(prec=precision):
        if version_object.release:
            version_components = version_object.release
            # Make sure there are always 5 version components for the correct
            # numerical result (1.3.5 should be larger than 1.2.3.4).
            version_components += (0,) * (5 - len(version_components))
            return Decimal(
                reduce(
                    lambda result, component: result * 10 ** 5 + component,
                    version_components
                )
            )
        else:
            result = Decimal(0)
            for position, char in enumerate(version_string):
                result += (
                    Decimal(ord(char) if char.isascii() else 0)
                    / (Decimal(128) ** (position + 1))
                )
            return result


def send_mass_html_mail(
        datatuple: Sequence[Tuple[str, str, str, Optional[str], Sequence[str] | None]],
        fail_silently: bool = False,
        auth_user: Optional[str] = None, auth_password: Optional[str] = None,
        connection: Optional[BaseEmailBackend] = None,
) -> int:
    """
    Given a datatuple of (subject, text_content, html_content, from_email,
    recipient_list), sends each message to each recipient list. Returns the
    number of emails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.
    """
    connection = connection or get_connection(
        username=auth_user, password=auth_password, fail_silently=fail_silently)
    messages: Sequence[EmailMessage] = []
    default_from = settings.DEFAULT_FROM_EMAIL
    for subject, text, html, from_email, recipients in datatuple:
        subject = ''.join(subject.splitlines())
        recipients = [r.strip() for r in recipients] if recipients else []
        message = AnymailMessage(
            subject, text, from_email or default_from, recipients,
            headers={'Reply-To': 'Pasporta Servo <saluton@pasportaservo.org>'})
        message.attach_alternative(html, 'text/html')
        # TODO: Implement custom one-click unsubscribe.
        message.esp_extra = {'MessageStream': 'broadcast'}
        if tag_match := re.match(r'\[\[([a-zA-Z0-9_-]+)\]\]', subject):
            message.tags = [tag_match.group(1)]
            message.subject = subject.removeprefix(tag_match.group()).strip()
        message.merge_data = {}  # Enable batch sending mode.
        setattr(message, 'mass_mail', True)
        messages.append(message)
    return connection.send_messages(messages) or 0


def sanitize_next(
        request: HttpRequest, from_post: bool = False, url: Optional[str] = None,
) -> str:
    """
    Verifies if the redirect target provided in the request is a safe one,
    meaning (mainly) not pointing to an external domain. Returns the target
    value in this case, and empty string otherwise.
    """
    if url is None:
        param_source = request.POST if from_post else request.GET
        redirect = param_source.get(settings.REDIRECT_FIELD_NAME, default='').strip()
    else:
        redirect = url
    if redirect and url_has_allowed_host_and_scheme(
                            url=redirect,
                            allowed_hosts={request.get_host()},
                            require_https=request.is_secure()):
        return redirect
    else:
        return ''


def sort_by[T](paths: Iterable[Any], iterable: Iterable[T]) -> Iterable[T]:
    """
    Sorts by a translatable name, using system locale for a better result.
    """
    locale.setlocale(locale.LC_ALL, settings.SYSTEM_LOCALE)
    for path in paths:
        iterable = sorted(
            iterable,
            key=lambda obj, attr_path=path: locale.strxfrm(str(getattr_(obj, attr_path)))
        )
    return iterable


@overload
def is_password_compromised(pwdvalue: str, full_list: Literal[False] = False) -> (
        tuple[None, None]
        | tuple[Literal[True], int] | Tuple[Literal[False], Literal[0]]
):
    ...  # pragma: no cover


@overload
def is_password_compromised(pwdvalue: str, full_list: Literal[True] = True) -> (
        tuple[None, None]
        | tuple[Literal[True], int, str] | Tuple[Literal[False], Literal[0], str]
):
    ...  # pragma: no cover


def is_password_compromised(pwdvalue: str, full_list: bool = False):
    """
    Uses the Pwned Passwords service of Have I Been Pwned to verify anonymously (using
    k-anonymity) if a password value has been compromised in the past, meaning that the
    value appears in a dump from a past breach elsewhere.
    """
    pwdhash = hashlib.sha1(pwdvalue.encode()).hexdigest().upper()
    try:
        result = requests.get(
            'https://api.pwnedpasswords.com/range/{}'.format(pwdhash[:5]),
            headers={
                'Add-Padding': 'true',
                'User-Agent': 'pasportaservo.org',
            }
        )
    except requests.exceptions.ConnectionError:
        return None, None
    else:
        if result.status_code != requests.codes.ok:
            return None, None

    for line in result.text.splitlines():
        suffix, count = line.split(':')
        count = int(count)
        if pwdhash.endswith(suffix):
            if count > 0:
                return (True, count) if not full_list else (True, count, result.text)
            break
    return (False, 0) if not full_list else (False, 0, result.text)
