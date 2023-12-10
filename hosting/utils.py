import logging
import os
import re
from typing import TYPE_CHECKING, Optional, cast
from uuid import uuid4

from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils import translation
from django.utils.deconstruct import deconstructible

import geocoder
from django_countries import Countries
from geocoder.opencage import OpenCageQuery, OpenCageResult

from core.models import SiteConfiguration
from maps import SRID
from maps.data import COUNTRIES_GEO

from .countries import countries_with_mandatory_region

if TYPE_CHECKING:  # pragma: no cover
    from .models import Profile


def geocode(
        query: str, country: str = '',
        private: bool = False, annotations: bool = False, multiple: bool = False,
) -> OpenCageQuery | None:
    """
    Utilizes the API of OpenCage to perform forward geocoding of the provided
    address.

    Args:
        `query` (str):
            The address to attempt geocoding. If the query is empty, nothing
            is done.
        `country` (str):
            Restrict geocoding to a specific country; a 2-letter code.
        `private` (bool):
            Whether to instruct OpenCage to not log this request.
        `annotations` (bool):
            Whether to include additional information (such as timezone,
            w3w, sunrise & sunset, currency, etc.) in the result.
            See https://opencagedata.com/api#annotations.
        `multiple` (bool):
            Whether to return just the first result, or several results
            if OpenCage has multiple hits.
    Returns:
        OpenCageQuery (with a Geo Point) or None.
    """
    config = cast(SiteConfiguration, SiteConfiguration.get_solo())
    key = config.mapping_services_api_keys.get('opencage')
    lang = translation.get_language()
    if not query:
        return
    params: dict[str, str | int] = {'language': lang}
    if not annotations:
        params.update({'no_annotations': int(not annotations)})
    if private:
        params.update({'no_record': int(private)})
    if country:
        params.update({'countrycode': country})
    result = geocoder.opencage(query, key=key, params=params, maxRows=15 if multiple else 1)
    logging.getLogger('PasportaServo.geo').debug(
        "Query: %s\n\tResult: %s\n\tConfidence: %d", query, result, result.confidence)
    result.point = Point(result.xy, srid=SRID) if result.xy else None
    result.session.close()
    return result


def geocode_city(
        cityname: str, country: str, state_province: Optional[str] = None,
) -> OpenCageResult | None:
    """
    Utilizes the API of OpenCage to perform forward geocoding of the provided
    city name (in an optional state / province).

    Args:
        `cityname` (str):
            The name of the city to attempt geocoding.
        `country` (str):
            The specific country the city is located in; a 2-letter code.
        `state_province` (str):
            Optionally, the state / province the city is located in.
            If provided, the full identification is attempted; if this yields
            no results, the utility falls back to just the city name.
    Returns:
        OpenCageResult or None.
    """
    if state_province:
        attempts = (', '.join([cityname, state_province]), )
        if country not in countries_with_mandatory_region():
            attempts += (cityname, )
    else:
        attempts = (cityname, )
    result = None
    for query in attempts:
        result_set = geocode(query, country, multiple=True)
        if not result_set:
            continue
        for single_result in result_set:
            result = cast(OpenCageResult, single_result)
            if result._components['_type'] in ('city', 'village') and result.bbox:
                result.remaining_api_calls = result_set.remaining_api_calls
                break
        else:
            result = None
        if result:
            break
    return result


def emulate_geocode_country(country_code: str) -> OpenCageResult:
    """
    Returns a manually built result which emulates forward geocoding of
    a country using OpenCage's API.
    This is needed because geocoding just the name of the country gives
    unpredictable results;  while combining the name with the country's
    code is unreliable (the query cannot be empty in any case).

    Args:
        `country_code` (str):
            The 2-letter code of the country.
    Returns:
        OpenCageResult (with a Geo Point).
    """
    country_code = country_code.upper()
    country_name = Countries().name(country_code)
    if country_name and country_code in COUNTRIES_GEO:
        data = {
            'components': {
                '_category': 'place',
                '_type': 'country',
                'country': country_name,
                'country_code': country_code,
            },
            'formatted': country_name,
            'geometry': {
                'lat': COUNTRIES_GEO[country_code]['center'][1],
                'lng': COUNTRIES_GEO[country_code]['center'][0],
            },
        }
    else:
        data = {}
    result = OpenCageResult(data)
    result.point = Point(result.xy, srid=SRID) if result.xy else None
    return result


def title_with_particule(value: str, particules: Optional[list[str]] = None) -> str:
    """
    Like string.title(), but do not capitalize surname particules.
    Regex matches a case insensitive (?i) particule
    at beginning of string or with space before (^|\W)
    and finishes by a space \W.
    """
    particule_list = ['van', 'de', 'des', 'del', 'von', 'av', 'af']
    particules = particules if particules else particule_list
    if value:
        value = value.title()
        particules_re = [(part, r'(^|\W)(?i:%s)(\W)' % part) for part in particules]
        for particule, particule_re in particules_re:
            value = re.sub(particule_re, r'\g<1>' + particule + r'\g<2>', value)
    return value


def value_without_invalid_marker(value: str) -> str:
    """
    Removes the prefix indicating non-validity from the given value.
    If the value is not invalid, it is returned as-is.
    """
    return (
        value[len(settings.INVALID_PREFIX):]
        if value.startswith(settings.INVALID_PREFIX)
        else value
    )


@deconstructible
class RenameAndPrefixAvatar(object):
    def __init__(self, path: str):
        self.sub_path = path

    def __call__(self, profile_instance: 'Profile', filename: str) -> str:
        ext = filename.split('.')[-1]
        if profile_instance.pk:
            filename = f'p{profile_instance.pk}_{uuid4().fields[0]:08x}'
        elif profile_instance.user:
            filename = f'u{profile_instance.user.pk}_{uuid4().fields[0]:08x}'
        else:
            filename = f'x{uuid4()}'
        filename = f'picture-{filename}.{ext.lower()}'
        return os.path.join(self.sub_path, filename)
