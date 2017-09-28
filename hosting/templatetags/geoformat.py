from django import template

from django_countries.data import COUNTRIES

register = template.Library()


@register.filter
def format_result(result):
    """Replace given country (-ujo) by the one from django_countries"""
    try:
        country = str(COUNTRIES[result.country.upper()])
    except KeyError:
        return result.address
    components = result.address.split(', ')[:-1]
    return ", ".join(components + [country])
