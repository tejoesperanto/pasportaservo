from django import template

register = template.Library()


@register.simple_tag
def cdn(library='', version=None):
    base = 'https://cdn.jsdelivr.net/'
    if not library:
        return base
    if library == 'ps':
        return '{}gh/tejoesperanto/pasportaservo@prod'.format(base)
    if library == 'bootstrap':
        return '{}gh/twbs/bootstrap{}{}/dist'.format(base, '@' if version else '', version or '')
    if library == 'jquery':
        return '{}gh/jquery/jquery{}{}/dist'.format(base, '@' if version else '', version or '')
    return ''
