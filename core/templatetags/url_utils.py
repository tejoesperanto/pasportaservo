from django import template
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
import random

register = template.Library()


@register.simple_tag(takes_context=True)
def domain(context, url=''):
    if 'request' in context:
        protocol = 'https' if context['request'].is_secure else 'http'
        _domain = get_current_site(context['request']).domain
    elif 'protocol' and 'domain' in context:  # Django emails
        protocol, _domain = context['protocol'], context['domain']
    elif 'site' in context:  # Postman emails
        _domain = context['site'].domain
        protocol = 'https' if 'pasportaservo.org' in _domain else 'http'
    else:  # Fallback
        if settings.DEBUG:
            protocol, _domain = 'http', 'localhost:8000'
        else:
            protocol, _domain = 'https', settings.ALLOWED_HOSTS[0]
    return '://'.join([protocol, _domain]) + url


@register.simple_tag
def random_identifier(length=None):
    try:
        length = int(length)
    except:
        length = None
    if length is None or length <= 0:
        length = random.randint(16, 48)
    return ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789_') for n in range(length))

