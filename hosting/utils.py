import os
import re
from uuid import uuid4

from django.conf import settings
from django.utils.deconstruct import deconstructible

from pyuca import Collator


def extend_bbox(boundingbox):
    """Extends the bounding box by x3 for its width, and x3 of its height."""
    s, n, w, e = [float(coord) for coord in boundingbox]
    delta_lat, delta_lng = n - s, e - w
    return [s - delta_lat, n + delta_lat, w - delta_lng, e + delta_lng]


def title_with_particule(value, particules=None):
    """Like string.title(), but do not capitalize surname particules.
    Regex maches case insensitive (?i) particule
    at begining of string or with space before (^|\W)
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


try:
    from django.utils.text import format_lazy as _format_lazy  # coming in Django 1.11
    format_lazy = _format_lazy
except ImportError:
    from django.utils.functional import keep_lazy_text
    format_lazy = keep_lazy_text(lambda s, *args, **kwargs: s.format(*args, **kwargs))
