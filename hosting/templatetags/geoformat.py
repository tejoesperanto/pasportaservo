from django import template
from django.contrib.gis.geos import LineString
from django.utils.safestring import mark_safe
from django_countries import Countries

from maps.data import COUNTRIES_GEO

from ..models import LocationConfidence

register = template.Library()


@register.filter
def format_geo_result(result):
    """
    Replace given country (-ujo) by the one from django_countries
    """
    if not result.country:
        return result.address or ""
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
def geo_result_country(result):
    """
    Return the country from django_countries corresponding to the
    one in the geocoding result.
    """
    try:
        return Countries().name(result.country_code.upper()) or result.country
    except (AttributeError, KeyError):
        return result.country


@register.filter
def is_location_in_country(place):
    if not place.location or place.location.empty:
        return False
    conf = place.location_confidence
    if conf >= LocationConfidence.ACCEPTABLE and conf != LocationConfidence.CONFIRMED:
        country_bbox = COUNTRIES_GEO[place.country]["bbox"]
        country_geom = LineString(
            country_bbox["northeast"], country_bbox["southwest"]
        ).envelope
        return place.location.within(country_geom)
    return conf == LocationConfidence.CONFIRMED


@register.filter
def format_dms(location, confidence=None):
    if not location or location.empty:
        return mark_safe("&#8593;&nbsp;&#xFF1F;&deg;, &#8594;&nbsp;&#xFF1F;&deg;")
    formatting = [
        (location.y, {True: ("N", "&#8593;"), False: ("S", "&#8595;")}),
        (location.x, {True: ("E", "&#8594;"), False: ("W", "&#8592;")}),
    ]
    dms = []
    for coord, signs in formatting:
        letter, arrow = signs[coord >= 0]
        minutes, seconds = divmod(abs(coord) * 3600, 60)
        degrees, minutes = map(int, divmod(minutes, 60))
        if confidence is None or confidence >= LocationConfidence.ACCEPTABLE:
            dms_seconds = f"{seconds:.3f}&#8243;"
        else:
            dms_seconds = ""
        dms.append(
            f"{arrow}&nbsp;{degrees}&deg;{minutes}&#8242;{dms_seconds}&thinsp;{letter}"
        )
    return mark_safe(", ".join(dms))


@register.filter
def geo_url_hash(result):
    """
    A Mapbox Map.options.hash from geocoder response
    https://www.mapbox.com/mapbox-gl-js/api/#map
    """
    if not result.latlng:
        return ""

    zoom = 6
    if not result.country:
        zoom = 4  # Continent, others...
    elif result.city:
        zoom = 8  # City or lower
    return f"#{zoom}/{result.lat}/{result.lng}"
