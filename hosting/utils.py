import os
import re
from uuid import uuid4

from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils.deconstruct import deconstructible

import geocoder
from pyuca import Collator


def geocode(query, country='', private=False, annotations=False):
    key = settings.OPENCAGE_API_KEY
    lang = settings.LANGUAGE_CODE
    if query:
        params = {'language': lang}
        if not annotations:
            params.update({'no_annotations': int(not annotations)})
        if private:
            params.update({'no_record': int(private)})
        if country:
            params.update({'countrycode': country})
        result = geocoder.opencage(query, key=key, params=params)
        result.point = Point(result.xy, srid=4326) if result.xy else None
        return result


def title_with_particule(value, particules=None):
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
        particules_re = [(part, r'(^|\W)(?i)%s(\W)' % part) for part in particules]
        for particule, particule_re in particules_re:
            value = re.sub(particule_re, '\g<1>' + particule + '\g<2>', value)
    return value


def split(value):
    """Improvement of "".split(), with support of apostrophe."""
    return re.split('\W+', value)


def value_without_invalid_marker(value):
    return (value[len(settings.INVALID_PREFIX):] if value.startswith(settings.INVALID_PREFIX) else value)


@deconstructible
class UploadAndRenameAvatar(object):
    def __init__(self, path):
        self.sub_path = path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        if instance.pk:
            filename = 'p{}_{}'.format(instance.pk, hex(uuid4().fields[0])[2:-1])
        elif instance.user:
            filename = 'u{}_{}'.format(instance.user.pk, hex(uuid4().fields[0])[2:-1])
        else:
            filename = 'x{}'.format(str(uuid4()))
        filename = 'picture-{}.{}'.format(filename, ext.lower())
        return os.path.join(self.sub_path, filename)


def sort_by_name(iterable):
    """Sort by a translatable name, using pyuca for a better result."""
    c = Collator()
    key = lambda obj: c.sort_key(str(obj.name))
    return sorted(iterable, key=key)
