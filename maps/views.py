from django.conf import settings
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from djgeojson.views import GeoJSONLayerView

from hosting.models import Place

HOURS = 3600


class WorldMapView(generic.TemplateView):
    template_name = 'maps/world_map.html'


class MapStyleView(generic.TemplateView):
    content_type = 'application/json'

    def get(self, request, *args, **kwargs):
        self.style = kwargs.pop('style')
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        return ['maps/styles/{}-gl-style.json'.format(self.style)]

    def get_context_data(self, **kwargs):
        return {
            'key': settings.OPENMAPTILES_API_KEY,
            'lang': settings.LANGUAGE_CODE,
        }


@method_decorator(cache_page(12 * HOURS), name='genuine_dispatch')
class PublicDataView(GeoJSONLayerView):
    geometry_field = 'location'
    precision = 2  # 0.01
    properties = [
        'city',
        'url',
        'owner_name',
    ]

    def dispatch(self, request, *args, **kwargs):
        request.META['HTTP_X_USER_STATUS'] = 'Authenticated' if request.user.is_authenticated else 'Anonymous'
        return self.genuine_dispatch(request, *args, **kwargs)

    @vary_on_headers('X-User-Status')
    def genuine_dispatch(self, request, *args, **kwargs):
        # Caching will take into account the header (via the Vary instruction), but
        # it must be added before the cache framework calculates the hashmap key.
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        by_visibility = Q(visibility__visible_online_public=True)
        if not self.request.user.is_authenticated:
            by_visibility &= Q(owner__pref__public_listing=True)
        return (
            Place.available_objects
                 .exclude(location__isnull=True)
                 .filter(by_visibility)
                 .prefetch_related('owner')
        )
