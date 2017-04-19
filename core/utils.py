from django.core.mail import get_connection, EmailMultiAlternatives
from django.conf import settings


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
    # stackoverflow.com/a/29920015/1019109 by stackoverflow.com/u/1157100/200-success
    from re import finditer
    matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return [m.group(0) for m in matches]

