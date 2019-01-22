from django.conf.urls import url
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy

from .views import (
    CountryDataView, EndpointsView, MapStyleView,
    MapTypeConfigureView, PublicDataView, WorldMapView,
)

urlpatterns = [
    url(r'^endpoints$', EndpointsView.as_view(), name='gis_endpoints'),
    url(format_lazy(r'^{places}\.geojson$', places=pgettext_lazy("URL", 'locations')),
        PublicDataView.as_view(), name='world_map_public_data'),
    url(format_lazy(
            r'^(?P<country_code>[A-Z]{{2}})(?:/{book}\:(?P<in_book>(0|1)))?/{places}\.geojson$',
            book=pgettext_lazy("URL", 'book'), places=pgettext_lazy("URL", 'locations')),
        CountryDataView.as_view(), name='country_map_data'),
    url(r'^(?P<style>\w+)-gl-style\.json$', MapStyleView.as_view(), name='map_style'),

    url(r'^$', WorldMapView.as_view(), name='world_map'),

    url(format_lazy(r'^{type}\:(?P<map_type>(0|3))/$', type=pgettext_lazy("URL", 'type')),
        MapTypeConfigureView.as_view(),
        name='map_type_setup'),
]
