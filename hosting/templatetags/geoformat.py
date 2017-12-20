from django import template

from django_countries.data import COUNTRIES

register = template.Library()


@register.filter
def format_geo_result(result):
    """
    Replace given country (-ujo) by the one from django_countries
    """
    if not result.country:
        return result.address or ''
    try:
        country = str(COUNTRIES[result.country.upper()])
    except KeyError:
        return result.address
    components = result.address.split(", ")[:-1]
    return ", ".join(components + [country])


@register.filter
def geo_url_hash(result):
    """
    A Mapbox Map.options.hash from geocoder response
    https://www.mapbox.com/mapbox-gl-js/api/#map
    """
    if not result.latlng:
        return ''

    zoom = 6
    if not result.country:
        zoom = 4  # Continent, others...
    elif result.city:
        zoom = 8  # City or lower
    return '#{}/{}/{}'.format(zoom, result.lat, result.lng)
