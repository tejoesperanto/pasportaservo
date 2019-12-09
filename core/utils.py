from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.http import is_safe_url


def send_mass_html_mail(datatuple, fail_silently=False, user=None, password=None,
                        connection=None):
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
        username=user, password=password, fail_silently=fail_silently)
    messages = []
    default_from = settings.DEFAULT_FROM_EMAIL
    for subject, text, html, from_email, recipients in datatuple:
        message = EmailMultiAlternatives(
            subject, text, default_from, recipients,
            headers={'Reply-To': 'Pasporta Servo <saluton@pasportaservo.org>'})
        message.attach_alternative(html, 'text/html')
        messages.append(message)
    return connection.send_messages(messages) or 0


def camel_case_split(identifier):
    """
    Converts AStringInCamelCase to a list of separate words.
    """
    # stackoverflow.com/a/29920015/1019109 -by- stackoverflow.com/u/1157100/200-success
    from re import finditer
    matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return [m.group(0) for m in matches]


def sanitize_next(request, from_post=False):
    """
    Verifies if the redirect target provided in the request is a safe one,
    meaning (mainly) not pointing to an external domain. Returns the target
    value in this case, and empty string otherwise.
    """
    param_source = request.POST if from_post else request.GET
    redirect = param_source.get(settings.REDIRECT_FIELD_NAME, default='').strip()
    if redirect and is_safe_url(url=redirect,
                                allowed_hosts={request.get_host()},
                                require_https=request.is_secure()):
        return redirect
    else:
        return ''
