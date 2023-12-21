from typing import Iterable, cast

from django import forms
from django.conf import settings
from django.contrib.gis.forms.widgets import BaseGeometryWidget
from django.urls import reverse_lazy
from django.utils.text import format_lazy

from . import SRID


class MapboxGlWidget(BaseGeometryWidget):
    """
    An OpenLayers/OpenStreetMap-based widget.
    """
    template_name = 'gis/mapbox-gl.html'
    map_srid = SRID
    map_height = 400
    default_lon = 5
    default_lat = 47
    has_input_fallback = False

    class Media:
        css = {
            'all': cast(
                Iterable[str], (
                    settings.MAPBOX_GL_CSS,
                )
            ),
        }
        js = cast(
            Iterable[str], (
                settings.MAPBOX_GL_JS,
            )
        )

    def __init__(self, attrs=None):
        super().__init__()
        for key in ('default_lon', 'default_lat', 'has_input_fallback'):
            self.attrs[key] = getattr(self, key)
        if attrs:
            self.attrs.update(attrs)

    @property
    def media(self):
        return (
            forms.Media(css=self.Media.css, js=self.Media.js)
            + forms.Media(js=(
                format_lazy('{}?format=js&type=widget', reverse_lazy('gis_endpoints')),
                'maps/mapbox-gl.eo.js',
                'maps/mapbox-gl-widget.js'))
        )

    def serialize(self, value):
        return value.json if value else ''


class AdminMapboxGlWidget(MapboxGlWidget):
    admin_site = True

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['admin_site'] = self.admin_site
        return context
