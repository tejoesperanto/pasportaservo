from django import template
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

register = template.Library()


@register.simple_tag(takes_context=True)
def domain(context, url=''):
    if 'request' in context:
        protocol = 'https' if context['request'].is_secure() else 'http'
        _domain = get_current_site(context['request']).domain
    elif 'protocol' in context and 'domain' in context:
        # Django emails
        protocol, _domain = context['protocol'], context['domain']
    elif 'site' in context:
        # Postman emails
        _domain = context['site'].domain
        protocol = 'https' if 'pasportaservo.org' in _domain else 'http'
    else:
        # Fallback
        if settings.DEBUG:
            protocol, _domain = 'http', 'localhost:8000'
        else:
            protocol, _domain = 'https', settings.ALLOWED_HOSTS[0]

    link = '{}://{}{}'.format(protocol, _domain, url)
    return link
