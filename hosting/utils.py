from __future__ import unicode_literals
import re

from django.core.mail import get_connection, EmailMultiAlternatives
from django.conf import settings


def extend_bbox(boundingbox):
    """Extends the bounding box by x3 for its width, and x3 of its height."""
    s, n, w, e = [float(coord) for coord in boundingbox]
    delta_lat, delta_lng = n - s, e - w
    return [s - delta_lat, n + delta_lat, w - delta_lng, e + delta_lng]


def title_with_particule(value, particules=None):
    """Like string.title(), but do not capitalize surname particules.
    Regex maches case insensitive (?i) particule
    at begining of string or with space before (^|\W)
    and finishes by a space \W.
    """
    particule_list = ['van', 'de', 'des', 'del', 'von', 'av', 'af']
    particules = particules if particules else particule_list
    if value:
        value = value.title()
        particules_re = [(part, r'(^|\W)(?i)%s(\W)' % part) for part in particules]
        for particule, particule_re in particules_re:
            value = re.sub(particule_re, '\g<1>' + particule + '\g<2>', value)
    return value


def split(value):
    """Improvement of "".split(), with support of apostrophe."""
    return re.split('\W+', value)


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
            headers = {'Reply-To': 'Pasporta Servo <saluton@pasportaservo.org>'})
        message.attach_alternative(html, 'text/html')
        messages.append(message)
    return connection.send_messages(messages) or 0
