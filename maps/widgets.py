from django.conf import settings
from django.contrib.gis.forms.widgets import BaseGeometryWidget


class MapboxGlWidget(BaseGeometryWidget):
    """
    An OpenLayers/OpenStreetMap-based widget.
    """
    template_name = 'gis/mapbox-gl.html'
    map_srid = 4326
    default_lon = 5
    default_lat = 47

    class Media:
        css = {
            'all': (
                settings.MAPBOX_GL_CSS,
            )
        }
        js = (
            settings.MAPBOX_GL_JS,
            'maps/mapbox-gl-widget.js'
        )

    def __init__(self, attrs=None):
        super().__init__()
        for key in ('default_lon', 'default_lat'):
            self.attrs[key] = getattr(self, key)
        if attrs:
            self.attrs.update(attrs)

    def serialize(self, value):
        return value.json if value else ''
