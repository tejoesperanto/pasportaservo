import functools
import hashlib
import locale
import operator
import re
from decimal import Decimal, localcontext as local_decimal_context
from typing import (
    Any, Callable, Iterable, Literal,
    Optional, Sequence, Tuple, cast, overload,
)

from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.backends.base import BaseEmailBackend
from django.http.request import HttpRequest, MediaType
from django.utils.functional import SimpleLazyObject, lazy, new_method_proxy
from django.utils.html import escape as html_escape
from django.utils.http import url_has_allowed_host_and_scheme

import requests
from anymail.message import AnymailMessage
from packvers import version


def getattr_(obj: Any, path: Iterable[str]) -> Any:
    return functools.reduce(getattr, path.split('.') if isinstance(path, str) else path, obj)


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


# Monkey-patch Django's SimpleLazyObject to support integers and operations on them.
setattr(SimpleLazyObject, '__int__', new_method_proxy(int))
setattr(SimpleLazyObject, '__add__', new_method_proxy(operator.add))
setattr(SimpleLazyObject, '__mul__', new_method_proxy(operator.mul))


def request_asks_for_json(request: HttpRequest) -> bool:
    """
    Checks whether this request stipulates that the response should be a JSON, as
    indicated in the "`Accept`" header. However, since most of the browsers include
    the value "`*/*`" in the header (meaning, no preference for the response type),
    the `MediaType.match()` method and `HttpRequest.accepts()` method (which relies
    on matching the media types, including wildcards) cannot be used - as also an
    HTML request would be classified as "JSON desired". Due to this, the check is
    done manually, in a strict manner.
    """
    # TODO: Revisit in Django 5.2.
    FLAG_ATTRIBUTE_NAME = 'needs_json'
    if not hasattr(request, FLAG_ATTRIBUTE_NAME):
        json = MediaType('application/json')
        setattr(request, FLAG_ATTRIBUTE_NAME, any(
            json.main_type == accepted.main_type and json.sub_type == accepted.sub_type
            for accepted in request.accepted_types
        ))
    return getattr(request, FLAG_ATTRIBUTE_NAME)


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
                functools.reduce(
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
        subject: str,
        text_content: str,
        html_content: str,
        from_email: Optional[str],
        customizations: dict[str, dict[str, str]],
        fail_silently: bool = True,
        auth_user: Optional[str] = None, auth_password: Optional[str] = None,
        connection: Optional[BaseEmailBackend] = None,
) -> int:
    """
    Given a `subject`, `text_content`, and `html_content`, sends a message to each
    recipient, indicated as a key of the `customizations` dict. If bulk sending is
    supported by the email backend, a single message will be dispatched, with
    placeholders in the form {{variable}} replaced by the ESP with values from the
    `customizations` dict. Otherwise, the replacements are done manually and a set
    of messages, equal in length to the number of recipients, is dispatched.
    Returns the number of emails that will be delivered.

    If `from_email` is None, the DEFAULT_FROM_EMAIL setting is used.
    When `auth_user` and `auth_password` are set, they're used to log in.
    If `auth_user` is None, the EMAIL_HOST_USER setting is used. If `auth_password`
    is None, the EMAIL_HOST_PASSWORD setting is used.
    """
    connection = connection or cast(
        BaseEmailBackend,  # get_connection never returns a None.
        get_connection(
            username=auth_user, password=auth_password, fail_silently=fail_silently,
        )
    )
    messages: Sequence[AnymailMessage] = []
    default_from = settings.DEFAULT_FROM_EMAIL

    bulk_sending_supported = False
    if bulk_sending_supported:  # pragma: no cover
        raise NotImplementedError
    else:
        variable_pattern = re.compile(r'\{\s*([a-z]+)\s*\}')

        def replacement_transform(
                match: re.Match[str], recipient: str, transform: Callable[[Any], str],
        ) -> str:
            replacement = customizations[recipient].get(match.group(1))
            return match.group(0) if replacement is None else str(transform(replacement))

        for recipient in customizations:
            text_transform = functools.partial(
                replacement_transform, recipient=recipient, transform=lambda v: v)
            html_transform = functools.partial(
                replacement_transform, recipient=recipient, transform=html_escape)
            single_subject = variable_pattern.sub(text_transform, subject)
            single_text = variable_pattern.sub(text_transform, text_content)
            single_html = variable_pattern.sub(html_transform, html_content)

            message = AnymailMessage(
                single_subject, single_text, from_email or default_from,
                [recipient.strip()],
                merge_data={},  # Enable batch sending mode.
            )
            message.attach_alternative(single_html, 'text/html')
            messages.append(message)

    subject_tag_re = re.compile(r'\[\[([a-zA-Z0-9_-]+)\]\]')
    for message in messages:
        message.subject = ''.join(message.subject.splitlines())
        if tag_match := re.match(subject_tag_re, message.subject):
            message.tags = [tag_match.group(1)]
            message.subject = message.subject.removeprefix(tag_match.group()).strip()
        message.metadata = {'env': settings.ENVIRONMENT}
        message.extra_headers.update({
            'Reply-To': 'Pasporta Servo <saluton@pasportaservo.org>',
        })
        # TODO: Implement custom one-click unsubscribe.
        message.esp_extra = {'MessageStream': 'broadcast'}
        setattr(message, 'mass_mail', True)

    num_sent = connection.send_messages(messages)
    if bulk_sending_supported:  # pragma: no cover
        # Only a single message is sent, but it will be delivered to multiple
        # recipients (individually).
        return len(customizations)
    else:
        # Since bulk dispatching is unavailable, a fallback of the manually
        # constructed set of individual messages is used.
        return num_sent or 0


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
