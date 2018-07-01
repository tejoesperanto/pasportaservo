from django.conf.urls import url
from django.utils.translation import pgettext_lazy

from .views import EndpointsView, MapStyleView, PublicDataView, WorldMapView

urlpatterns = [
    url(r'^endpoints$', EndpointsView.as_view(), name='gis_endpoints'),
    url(r'^{}\.geojson$'.format(pgettext_lazy("URL", 'locations')),
        PublicDataView.as_view(), name='world_map_public_data'),
    url(r'^(?P<style>\w+)-gl-style\.json$', MapStyleView.as_view(), name='map_style'),
    url(r'^$', WorldMapView.as_view(), name='world_map'),
]
