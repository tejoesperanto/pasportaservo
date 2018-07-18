from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from djgeojson.views import GeoJSONLayerView

from core.models import SiteConfiguration
from hosting.models import Place

HOURS = 3600


class WorldMapView(generic.TemplateView):
    template_name = 'maps/world_map.html'


class EndpointsView(generic.View):
    def get(self, request, *args, **kwargs):
        format = request.GET.get('format', None)
        endpoints = {
            'rtl_plugin': settings.MAPBOX_GL_RTL_PLUGIN,
            'world_map_style': reverse_lazy('map_style', kwargs={'style': 'positron'}),
            'place_map_style': reverse_lazy('map_style', kwargs={'style': 'klokantech'}),
            'widget_style': reverse_lazy('map_style', kwargs={'style': 'positron'}),
            'world_map_data': reverse_lazy('world_map_public_data'),
        }
        if format == 'js':
            return HttpResponse(
                'var GIS_ENDPOINTS = {!s};'.format(endpoints),
                content_type='application/javascript')
        else:
            return JsonResponse(endpoints)


class MapStyleView(generic.TemplateView):
    content_type = 'application/json'

    def get(self, request, *args, **kwargs):
        self.style = kwargs.pop('style')
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        return ['maps/styles/{}-gl-style.json'.format(self.style)]

    def get_context_data(self, **kwargs):
        return {
            'key': SiteConfiguration.get_solo().openmaptiles_api_key,
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

    class GeoPlace(Place):
        class Meta:
            proxy = True

        @property
        def url(self):
            return self.get_absolute_url()

        @property
        def owner_name(self):
            return self.owner.name or self.owner.INCOGNITO

        @property
        def owner_url(self):
            return self.owner.get_absolute_url()

        @property
        def owner_avatar(self):
            return self.owner.avatar_url

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
            self.GeoPlace
                .available_objects
                .exclude(location__isnull=True)
                .filter(by_visibility)
                .prefetch_related('owner')
        )
