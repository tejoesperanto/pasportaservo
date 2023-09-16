import json
import logging
import re
from urllib.parse import quote_plus, unquote_plus

from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.db.models import BooleanField, Case, Count, F, Prefetch, Q, When
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseRedirectBase
from django.urls import reverse
from django.utils.encoding import uri_to_iri
from django.utils.translation import pgettext
from django.views import generic

import geocoder
from django_countries.fields import Country
from el_pagination.views import AjaxListView

from core.auth import PERM_SUPERVISOR, AuthMixin, AuthRole
from core.forms import FeedbackForm
from core.templatetags.utils import compact
from maps import SRID
from maps.utils import bufferize_country_boundaries

from ..filters.search import SearchFilterSet
from ..models import Condition, LocationConfidence, Phone, Place, TravelAdvice
from ..utils import emulate_geocode_country, geocode


class HttpResponseTemporaryRedirect(HttpResponseRedirectBase):
    """
        The 307 Temporary Redirect instructs the browser to load
        a new URL, preserving the request body and method.
    """
    status_code = 307


class PlaceListView(generic.ListView):
    model = Place


class PlacePaginatedListView(AjaxListView):
    model = Place


class PlaceStaffListView(AuthMixin, PlaceListView):
    """
    A place for supervisors to see an overview of and manage hosts in their
    area of responsibility.
    """
    template_name = 'hosting/place_list_supervisor.html'
    display_fair_usage_condition = True
    minimum_role = AuthRole.SUPERVISOR

    def dispatch(self, request, *args, **kwargs):
        self.country = Country(kwargs['country_code'])
        kwargs['auth_base'] = self.country
        self.in_book_status = {'0': False, '1': True, None: None}[kwargs.get('in_book')]
        self.invalid_emails = kwargs.get('email')
        return super().dispatch(request, *args, **kwargs)

    def get_owner(self, object):
        return None

    def get_location(self, object):
        return object

    def get_queryset(self):
        self.base_qs = self.model.available_objects.filter(country=self.country.code).filter(
            Q(visibility__visible_online_public=True)
            | Q(in_book=True, visibility__visible_in_book=True)
        )
        if self.in_book_status is not None:
            narrowing_func = getattr(self.base_qs, 'filter' if self.in_book_status else 'exclude')
            qs = narrowing_func(in_book=True, visibility__visible_in_book=True)
        else:
            qs = self.base_qs
        if self.invalid_emails:
            qs = qs.filter(owner__user__email__startswith=settings.INVALID_PREFIX)
        qs = qs.annotate(
            location_valid=Case(
                When(
                    Q(location__isnull=False) & ~Q(location=Point([])),
                    then=True),
                default=False, output_field=BooleanField()
            ),
            location_inaccurate=Case(
                When(
                    Q(location_valid=True) & Q(location_confidence__lt=LocationConfidence.ACCEPTABLE),
                    then=True),
                default=False, output_field=BooleanField()
            ),
            location_accurate=Case(
                When(
                    Q(location_valid=True) & Q(location_confidence__gte=LocationConfidence.ACCEPTABLE),
                    then=True),
                default=False, output_field=BooleanField()
            ),
        )
        phones_prefetch = Prefetch(
            'owner__phones',
            queryset=Phone.objects_raw.select_related('visibility')
        )
        return (qs.select_related('owner', 'owner__user')
                  .prefetch_related(phones_prefetch)
                  .order_by('-confirmed', 'checked', 'owner__last_name'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        in_book_status_filter = Q(in_book=True) & Q(visibility__visible_in_book=True)
        counts_overall = {
            'in_book_count':
                Count('pk', filter=in_book_status_filter),
            'not_in_book_count':
                Count('pk', filter=~in_book_status_filter),
            'invalid_emails_count':
                Count('pk', filter=Q(owner__user__email__startswith=settings.INVALID_PREFIX)),
        }
        counts_qs = self.base_qs._clone()
        counts_qs.query.annotations.clear()
        context.update(counts_qs.aggregate(**counts_overall))

        if self.in_book_status is True:
            context['place_count'] = context['in_book_count']
        elif self.in_book_status is False:
            context['place_count'] = context['not_in_book_count']
        else:
            context['place_count'] = context['in_book_count'] + context['not_in_book_count']
        # Forcing evaluation of the query result at this stage avoids repeated queries of the DB.
        # Counting could be done with a, b = zip(*status); a.count(True) but that would create two
        # additional lists of the length of `object_list`.
        status = ([place.pk, place.checked, place.confirmed] for place in list(self.object_list))
        context['checked_count'] = sum(1 for place_status in status if place_status[1])
        context['confirmed_count'] = sum(1 for place_status in status if place_status[2])
        context['not_confirmed_count'] = context['place_count'] - context['confirmed_count']

        context.update({
            f'MAPBOX_GL_{setting}': getattr(settings, f'MAPBOX_GL_{setting}')
            for setting in ('CSS', 'CSS_INTEGRITY', 'JS', 'JS_INTEGRITY')
        })
        coords = bufferize_country_boundaries(self.country.code)
        if coords:
            context['country_coordinates'] = json.dumps(coords)

        return context


class SearchView(PlacePaginatedListView):
    queryset = Place.objects.filter(
        visibility__visible_online_public=True,
        owner__death_date__isnull=True)
    paginate_first_by = 25
    paginate_by = 25
    display_fair_usage_condition = True

    def get(self, request, *args, **kwargs):
        if settings.SEARCH_FIELD_NAME in request.GET:
            return HttpResponseRedirect(
                self.transpose_query_to_url_kwarg(request.GET))

        self.prepare_search(request, kwargs.get('query'), None, kwargs.get('cache'))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not kwargs.get('query') and request.POST.get(settings.SEARCH_FIELD_NAME):
            if request.session.get('connection_browser') == 'Firefox':
                # Ugly workaround because Firefox forgets the request data.
                # https://bugzilla.mozilla.org/show_bug.cgi?id=1805182
                pass
            else:
                return HttpResponseTemporaryRedirect(
                    self.transpose_query_to_url_kwarg(request.POST))

        query = kwargs.get('query') or request.POST.get(settings.SEARCH_FIELD_NAME)
        self.prepare_search(request, query, request.POST, kwargs.get('cache'))
        return super().get(request, *args, **kwargs)

    def transpose_query_to_url_kwarg(self, source):
        """
        If the search query is given via the ps_q request parameter,
        convert it to a URL-encoded keyword param of the `search` path.
        """
        # Keeping Unicode in URL, replacing space with '+'.
        query = uri_to_iri(quote_plus(compact(source[settings.SEARCH_FIELD_NAME])))
        params = {'query': query} if query else None
        return reverse('search', kwargs=params)

    def get_identifier_for_cache(self, request=None):
        """
        How the cached results are identified: if the user is authenticated,
        just use the user's ID; otherwise (user is not authenticated), use
        # the key of the anonymous session.
        """
        request = request or self.request
        if not request.user.id and not request.session.session_key:
            # Make sure the session has a key.
            request.session.cycle_key()
        return request.user.id or request.session.session_key

    def prepare_search(self, request, query, extended_query=None, cached_id=None):
        # URL-decode and trim query, avoiding query=None.
        self.query = compact(unquote_plus(query or ''))
        # Allow extended querying (that is, "advanced search") only to
        # authenticated users who have a profile and to administrators
        # regardless of their profile status.
        if not request.user.is_authenticated:
            self.extended_query = None
        elif not request.user_has_profile and not request.user.is_superuser:
            self.extended_query = None
        else:
            self.extended_query = extended_query
        # Exclude places whose owner blocked unauthenticated viewing.
        if not request.user.is_authenticated:
            self.queryset = self.queryset.exclude(owner__pref__public_listing=False)
        # Exclude places whose owner's profile is deleted, unless the
        # viewing user is a supervisor or an administrator.
        if not request.user.has_perm(PERM_SUPERVISOR):
            self.queryset = self.queryset.exclude(owner__deleted_on__isnull=False)
        # Fetch the hosting conditions for all displayed places in one
        # batch to reduce trips to the database, when the viewing user
        # is authenticated. For unauthenticated viewing, no conditions
        # are shown.
        if request.user.is_authenticated:
            conditions_prefetch = Prefetch(
                'conditions',
                queryset=Condition.objects.filter(restriction=False)
            )
            # Note: We are fetching the same Condition objects for multiple places.
            #       Probably it would be better to retrieve references to single
            #       cached instances instead, but this feels like over-engineering.
            self.queryset = self.queryset.prefetch_related(conditions_prefetch)

        if cached_id:
            sess_id = self.get_identifier_for_cache(request)
            cached_search = cache.get(f'search-results:{sess_id}:{cached_id}', default={})
            if isinstance(cached_search, dict):
                self._cached_db_query = cached_search.get('query')
                for paging_setting, how_much in cached_search.get('paging', {}).items():
                    setattr(self, f'paginate_{paging_setting}', how_much)
                self.query = cached_search.get('search-text', '')
            else:
                self._cached_db_query = cached_search
            self._cached_id = cached_id

        self.place_filter = SearchFilterSet(self.extended_query, self.queryset, request=request)

    def parse_user_query(self):
        parsed_query = {
            'query': self.query,
        }
        if self.query:
            translated_tag = pgettext("URL", "countrycode")
            tag = f'countrycode|{translated_tag}'
            country_code = re.search(rf'(?:^|\W)(?:{tag}):([A-Z]{{2}})(?:\W|$)', self.query)
            if country_code:
                country_code = country_code.group(1)
            remaining_query = re.sub(rf'(^|\W)(?:{tag}):\w*?(?=\W|$)', r'\1', self.query)
            parsed_query.update({
                'query': remaining_query.strip(),
                'country_code': country_code,
            })
        return parsed_query

    def get_queryset(self):
        most_recent_moniker, most_recent = pgettext("value::plural", "MOST RECENT"), False
        if self.query in (most_recent_moniker, most_recent_moniker.replace(" ", "_")):
            most_recent = True
            self.query = ''

        # If cached results are available, attempt to use them.
        if hasattr(self, '_cached_db_query'):
            if self._cached_db_query:
                qs = self.queryset.all()  # Clone the existing queryset.
                qs.query = self._cached_db_query
                qs = qs.all()  # Refresh the queryset according to the previous query.
            else:
                # A previously run query is requested but is no longer in cache.
                # Or, the requested query does not belong to the current user.
                qs = self.queryset.none()
            return qs

        # No cached results: perform the full query.
        qs = (
            self.place_filter.qs
            .select_related('owner', 'owner__user')
            .defer('address', 'description', 'short_description', 'owner__description')
        )

        parsed_query = self.parse_user_query()
        if 'country_code' in parsed_query and not parsed_query['query']:
            self.result = emulate_geocode_country(parsed_query['country_code'])
        else:
            self.result = geocode(
                parsed_query['query'], country=parsed_query.get('country_code'))
        self.cleaned_query = parsed_query['query']
        if self.query and self.result.point:
            point_category = getattr(self.result, '_components', {}).get('_category')
            point_type = getattr(self.result, '_components', {}).get('_type')
            locality_found_flags = [
                self.result.country and not self.result.country_code,
                self.result.state,
                self.result.city,
                point_category == 'place' and point_type and point_type != 'country',
            ]
            if any(locality_found_flags):
                self.inhabited_place_search = point_category == 'place'
                search_queryset = (
                    qs
                    .annotate(distance=Distance('location', self.result.point))
                    .order_by('distance')
                )
                self.cache_queryset_query(search_queryset)
                return search_queryset
            elif self.result.country:  # We assume it's a country.
                self.paginate_first_by = 50
                self.paginate_orphans = 5
                self.country_search = point_type == 'country' if point_type else True
                search_queryset = (
                    qs
                    .filter(country=self.result.country_code.upper())
                    .order_by(F('owner__user__last_login').desc(nulls_last=True), '-id')
                )
                self.cache_queryset_query(search_queryset)
                return search_queryset
        position = geocoder.ip(self.request.META['HTTP_X_REAL_IP']
                               if settings.ENVIRONMENT not in ('DEV', 'TEST')
                               else "188.166.58.162")
        position.point = Point(position.xy, srid=SRID) if position.xy else None
        logging.getLogger('PasportaServo.geo').debug(
            "User's position: %s, %s",
            position.address if position.ok and position.address else "UNKNOWN",
            position.xy if position.ok else position.error
        )
        position.session.close()
        if position.point and not most_recent:
            # Results are sorted by distance from user's current location, but probably
            # it is better not to creep users out by unexpectedly using their location.
            search_queryset = (
                qs
                .annotate(internal_distance=Distance('location', position.point))
                .order_by('internal_distance')
            )
        else:
            search_queryset = (
                qs
                .order_by(F('owner__user__last_login').desc(nulls_last=True), '-id')
            )

        # Cache the calculated result.
        self.cache_queryset_query(search_queryset)
        return search_queryset

    def cache_queryset_query(self, queryset):
        sess_id = self.get_identifier_for_cache()
        self._cached_id = hex(id(queryset))[2:]
        cached_search = {
            'query': queryset.query,
            'paging': {
                setting[len('paginate_'):]: getattr(self, setting)
                for setting in set(self.__dict__.keys()) | set(self.__class__.__dict__.keys())
                if setting.startswith('paginate_')
            },
            'search-text': self.query,
        }
        cache.set(f'search-results:{sess_id}:{self._cached_id}', cached_search, timeout=2*60*60)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.place_filter
        form = self.place_filter.form
        context['filtered_by'] = (
            set(form.changed_data).intersection(
                f for f, v in getattr(form, 'cleaned_data', {}).items() if v)
        ) if form.is_bound else []
        context['queryset_cache_id'] = self._cached_id
        context['feedback_form'] = FeedbackForm()

        if (getattr(self, 'country_search', False)
                and hasattr(self, 'result') and self.result.country_code):
            context['country_results_count'] = context['object_list'].count()
            context['country_advisories'] = (
                TravelAdvice.get_for_country(self.result.country_code.upper())
            )

        return context
