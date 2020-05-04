from django import template

from django_countries import Countries

register = template.Library()


@register.filter
def format_geo_result(result):
    """
    Replace given country (-ujo) by the one from django_countries
    """
    if not result.country:
        return result.address or ''
    try:
        country = Countries().name(result.country_code.upper())
    except Exception:
        return result.address
    else:
        if not country:
            return result.address
    # The name of the country is not necessarily the last-most component of
    # the address.  For example, in some countries the postal code would be
    # located at the very end of the address string.
    components = [part for part in result.address.split(", ") if part != result.country]
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
