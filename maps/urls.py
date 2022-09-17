from django.urls import path, re_path, register_converter
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy

from .views import (
    CountryDataView, EndpointsView, MapStyleView,
    MapTypeConfigureView, PublicDataView, WorldMapView,
)


class MapTypeConverter:
    regex = '0|3'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return str(value)


register_converter(MapTypeConverter, 'map_type')


urlpatterns = [
    path(
        'endpoints/',
        EndpointsView.as_view(), name='gis_endpoints'),
    path(
        format_lazy('{places}.geojson', places=pgettext_lazy("URL", 'locations')),
        PublicDataView.as_view(), name='world_map_public_data'),
    re_path(
        format_lazy(
            r'^(?P<country_code>[A-Z]{{2}})'
            + r'(?:/{book}\:(?P<in_book>(0|1)))?'
            + r'/{places}\.geojson$',
            book=pgettext_lazy("URL", 'book'), places=pgettext_lazy("URL", 'locations')),
        CountryDataView.as_view(), name='country_map_data'),
    path(
        '<slug:style>-gl-style.json',
        MapStyleView.as_view(), name='map_style'),

    path(
        '', WorldMapView.as_view(), name='world_map'),

    path(
        format_lazy('{type}:<map_type:map_type>/', type=pgettext_lazy("URL", 'type')),
        MapTypeConfigureView.as_view(), name='map_type_setup'),
]
