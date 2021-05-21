import logging
import os
import re
from uuid import uuid4

import geocoder
from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils.deconstruct import deconstructible

from core.models import SiteConfiguration
from maps import SRID

from .countries import countries_with_mandatory_region


def geocode(query, country="", private=False, annotations=False, multiple=False):
    key = SiteConfiguration.get_solo().opencage_api_key
    lang = settings.LANGUAGE_CODE
    if not query:
        return
    params = {"language": lang}
    if not annotations:
        params.update({"no_annotations": int(not annotations)})
    if private:
        params.update({"no_record": int(private)})
    if country:
        params.update({"countrycode": country})
    result = geocoder.opencage(
        query, key=key, params=params, maxRows=15 if multiple else 1
    )
    logging.getLogger("PasportaServo.geo").debug(
        "Query: %s\n\tResult: %s\n\tConfidence: %d", query, result, result.confidence
    )
    result.point = Point(result.xy, srid=SRID) if result.xy else None
    return result


def geocode_city(cityname, country, state_province=None):
    if state_province:
        attempts = (", ".join([cityname, state_province]),)
        if country not in countries_with_mandatory_region():
            attempts += (cityname,)
    else:
        attempts = (cityname,)
    for query in attempts:
        result_set = geocode(query, country, multiple=True)
        for result in result_set:
            if result._components["_type"] in ("city", "village") and result.bbox:
                result.remaining_api_calls = result_set.remaining_api_calls
                break
        else:
            result = None
        if result:
            break
    return result


def title_with_particule(value, particules=None):
    """
    Like string.title(), but do not capitalize surname particules.
    Regex matches a case insensitive (?i) particule
    at beginning of string or with space before (^|\W)
    and finishes by a space \W.
    """
    particule_list = ["van", "de", "des", "del", "von", "av", "af"]
    particules = particules if particules else particule_list
    if value:
        value = value.title()
        particules_re = [(part, r"(^|\W)(?i:%s)(\W)" % part) for part in particules]
        for particule, particule_re in particules_re:
            value = re.sub(particule_re, "\g<1>" + particule + "\g<2>", value)
    return value


def split(value):
    """Improvement of "".split(), with support of apostrophe."""
    return re.split("\W+", value)


def value_without_invalid_marker(value):
    return (
        value[len(settings.INVALID_PREFIX) :]
        if value.startswith(settings.INVALID_PREFIX)
        else value
    )


@deconstructible
class UploadAndRenameAvatar(object):
    def __init__(self, path):
        self.sub_path = path

    def __call__(self, instance, filename):
        ext = filename.split(".")[-1]
        if instance.pk:
            filename = "p{}_{}".format(instance.pk, hex(uuid4().fields[0])[2:-1])
        elif instance.user:
            filename = "u{}_{}".format(instance.user.pk, hex(uuid4().fields[0])[2:-1])
        else:
            filename = "x{}".format(str(uuid4()))
        filename = "picture-{}.{}".format(filename, ext.lower())
        return os.path.join(self.sub_path, filename)
