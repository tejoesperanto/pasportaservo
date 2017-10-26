from django.conf.urls import url

from .views import MapStyleView, PublicDataView, WorldMapView

urlpatterns = [
    url(r'^lokoj\.geojson$', PublicDataView.as_view(), name='public_data'),
    url(r'^(?P<style>\w+)-gl-style\.json$', MapStyleView.as_view(), name='world_map_style'),
    url(r'^$', WorldMapView.as_view(), name='world_map'),
]
