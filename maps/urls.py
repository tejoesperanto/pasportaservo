from django.conf.urls import url

from .views import PublicDataView, WorldMapView

urlpatterns = [
    url(r'^lokoj\.geojson$', PublicDataView.as_view(), name='public_data'),
    url(r'^$', WorldMapView.as_view(), name='world_map'),
]
