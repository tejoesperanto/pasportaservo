from __future__ import unicode_literals
import re


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
    value = value.title()
    particules_re = [(part, r'(^|\W)(?i)%s(\W)' % part) for part in particules]
    for particule, particule_re in particules_re:
        value = re.sub(particule_re, '\g<1>' + particule + '\g<2>', value)
    return value


def split(value):
    """Improvement of "".split(), with support of apostrophe."""
    return re.split('\W+', value)
