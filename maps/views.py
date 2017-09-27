from django.views import generic
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from djgeojson.views import GeoJSONLayerView


from hosting.models import Place

hours = 3600


class WorldMapView(generic.TemplateView):
    template_name = 'maps/world_map.html'


@method_decorator(cache_page(12 * hours), name='dispatch')
class PublicDataView(GeoJSONLayerView):
    geometry_field = 'location'
    precision = 2  # 0.01
    properties = [
        'city',
        'url',
        'owner_name',
    ]

    def get_queryset(self):
        return (
            Place.available_objects
                 .exclude(location__isnull=True)
                 .prefetch_related('owner')
        )
