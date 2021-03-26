from django.conf import settings
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from django_countries.fields import Country
from djgeojson.views import GeoJSONLayerView

from core.auth import SUPERVISOR, AuthMixin
from core.models import SiteConfiguration
from core.utils import sanitize_next
from hosting.models import Place

HOURS = 3600


class WorldMapView(generic.TemplateView):
    template_name = 'maps/world_map.html'


class MapTypeConfigureView(generic.View):
    """
    Allows the current user to configure the type of the maps displayed on the website for the
    current session, i.e. not persisted for the account and not shared between the sessions.
    Currently two types are supported: fully-functional (requires WebGL) and basic (static image).
    """
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        map_type = kwargs.pop('map_type')
        if request.is_ajax():
            response = JsonResponse({'success': 'map-type-configured'})
        else:
            response = HttpResponseRedirect(sanitize_next(request, from_post=True) or reverse_lazy('home'))
        response.set_cookie('maptype', map_type, max_age=31557600)
        return response


class EndpointsView(generic.View):
    def get(self, request, *args, **kwargs):
        format = request.GET.get('format', None)
        type = request.GET.get('type', '')
        endpoints = {
            'rtl_plugin': settings.MAPBOX_GL_RTL_PLUGIN,
        }
        if type == 'world':
            endpoints.update({
                'world_map_style': reverse_lazy('map_style', kwargs={'style': 'positron'}),
                'world_map_data': reverse_lazy('world_map_public_data'),
            })
        if type == 'region':
            # This usage of GET params is safe, because the values are restricted by the URL
            # regex: country_code can only be 2 capital letters; in_book either 0 or 1 only.
            region_kwargs = {'country_code': request.GET['country']}
            if 'in_book' in request.GET:
                region_kwargs.update({'in_book': request.GET['in_book']})
            endpoints.update({
                'region_map_style': reverse_lazy('map_style', kwargs={'style': 'klokantech'}),
                'region_map_data': reverse_lazy('country_map_data', kwargs=region_kwargs),
            })
        if type == 'place':
            endpoints.update({
                'place_map_style': reverse_lazy('map_style', kwargs={'style': 'klokantech'}),
            })
        if type == 'place-printed':
            endpoints.update({
                'place_map_style': reverse_lazy('map_style', kwargs={'style': 'toner'}),
                'place_map_attrib': 0,
            })
        if type == 'widget':
            endpoints.update({
                'widget_style': reverse_lazy('map_style', kwargs={'style': 'positron'}),
            })
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


class PlottablePlace(Place):
    """
    Wrapper around the Place to provide additional properties we want to show on map.
    """
    class Meta:
        proxy = True

    @property
    def url(self):
        return self.get_absolute_url()

    @property
    def owner_name(self):
        return self.owner.name or self.owner.INCOGNITO

    @property
    def owner_full_name(self):
        return self.owner.get_fullname_display(non_empty=True)

    @property
    def owner_url(self):
        return self.owner.get_absolute_url()

    @property
    def owner_avatar(self):
        return self.owner.avatar_url


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
            PlottablePlace.objects_raw
            .filter(available=True)
            .exclude(Q(location__isnull=True) | Q(location=Point([])) | Q(owner__death_date__isnull=False))
            .filter(by_visibility)
            .select_related('owner')
            .defer('address', 'description', 'short_description', 'owner__description')
        )


class CountryDataView(AuthMixin, GeoJSONLayerView):
    geometry_field = 'location'
    properties = [
        'owner_full_name',
        'checked', 'confirmed',
        'in_book',
    ]
    minimum_role = SUPERVISOR

    def dispatch(self, request, *args, **kwargs):
        self.country = Country(kwargs['country_code'])
        self.in_book_status = {'0': False, '1': True, None: None}[kwargs['in_book']]
        kwargs['auth_base'] = self.country
        return super().dispatch(request, *args, **kwargs)

    def get_owner(self, object):
        return None

    def get_location(self, object):
        return object

    def get_queryset(self):
        queryset = (
            PlottablePlace.available_objects
            .filter(country=self.country.code)
            .filter(
                Q(visibility__visible_online_public=True) | Q(in_book=True, visibility__visible_in_book=True)
            )
        )
        if self.in_book_status is not None:
            narrowing_func = getattr(queryset, 'filter' if self.in_book_status else 'exclude')
            queryset = narrowing_func(in_book=True, visibility__visible_in_book=True)
        return (
            queryset
            .exclude(Q(location__isnull=True) | Q(location=Point([])))
            .select_related('owner')
            .defer('address', 'description', 'short_description', 'owner__description')
        )
