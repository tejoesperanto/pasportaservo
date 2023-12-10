import json
from typing import TYPE_CHECKING, Any, cast

from django import template
from django.contrib.gis.geos import LineString, Point
from django.utils.safestring import SafeString, mark_safe

from django_countries import Countries

from maps.data import COUNTRIES_GEO

from ..models import LocationConfidence

if TYPE_CHECKING:  # pragma: no cover
    from ..models import Place


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
def is_location_in_country(place: 'Place') -> bool:
    if not place.location or place.location.empty:
        return False
    conf = place.location_confidence
    if conf >= LocationConfidence.ACCEPTABLE and conf != LocationConfidence.CONFIRMED:
        country_bbox = COUNTRIES_GEO[place.country]['bbox']
        country_geom = LineString(country_bbox['northeast'], country_bbox['southwest']).envelope
        return place.location.within(country_geom)
    return conf == LocationConfidence.CONFIRMED


@register.filter
def format_dms(location: Point, confidence: LocationConfidence | int | None = None) -> SafeString:
    if not location or location.empty:
        return mark_safe("&#8593;&nbsp;&#xFF1F;&deg;, &#8594;&nbsp;&#xFF1F;&deg;")
    formatting = [
        (location.y, {True: ('N', '&#8593;'), False: ('S', '&#8595;')}),
        (location.x, {True: ('E', '&#8594;'), False: ('W', '&#8592;')}),
    ]
    dms: list[str] = []
    for coord, signs in formatting:
        letter, arrow = signs[coord >= 0]
        minutes, seconds = divmod(abs(coord) * 3600, 60)
        degrees, minutes = map(int, divmod(minutes, 60))
        if confidence is None or confidence >= LocationConfidence.ACCEPTABLE:
            dms_seconds = f"{seconds:.3f}&#8243;"
        else:
            dms_seconds = ""
        dms.append(f"{arrow}&nbsp;{degrees}&deg;{minutes}&#8242;{dms_seconds}&thinsp;{letter}")
    return mark_safe(', '.join(dms))


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
    return f'#{zoom}/{result.lat}/{result.lng}'


GeoJsonPart = dict[str, Any]


@register.filter
def geojsonfeature_styling(
        serialized_geojson: str,
        params: GeoJsonPart | list[GeoJsonPart],
) -> str:
    geojson: GeoJsonPart = json.loads(serialized_geojson) or {}
    features = None
    if geojson.get('type') == 'Feature':
        features = [geojson]
        if isinstance(params, dict):
            params = [params]
    if geojson.get('type') == 'FeatureCollection':
        features = geojson.get('features', [])
        if isinstance(params, dict):
            params = [params] * len(features)
    if features is None or params is None:
        return serialized_geojson

    for feature, styling_properties in zip(features, cast(list[GeoJsonPart], params)):
        feature.setdefault('properties', {})
        for property, value in styling_properties.items():
            if property == 'crs':
                if not value:
                    geojson.pop('crs', None)
            else:
                feature['properties'][property.replace('__', '-')] = value
    return json.dumps(geojson)
