from django.conf import settings
from django.views import generic
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from accept_language import parse_accept_language
from djgeojson.views import GeoJSONLayerView


from hosting.models import Place

hours = 3600


class WorldMapView(generic.TemplateView):
    template_name = 'maps/world_map.html'


class MapStyleView(generic.TemplateView):
    content_type = 'application/json'

    def get(self, request, *args, **kwargs):
        self.style = kwargs['style']
        self.lang = self.get_language()
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        return ['maps/styles/{}-gl-style.json'.format(self.style)]

    def get_language(self):
        languages = parse_accept_language(self.request.META['HTTP_ACCEPT_LANGUAGE'])
        for lang in languages:
            if lang.language in settings.OPENMAPTILES_LANGUAGES:
                return lang.language
        return 'en'

    def get_context_data(self, **kwargs):
        return {
            'key': settings.OPENMAPTILES_API_KEY,
            'lang': self.lang
        }


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
