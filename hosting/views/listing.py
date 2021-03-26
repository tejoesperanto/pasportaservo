import json
import logging
from urllib.parse import quote_plus, unquote_plus

from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import BooleanField, Case, Q, When
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.encoding import uri_to_iri
from django.utils.translation import pgettext
from django.views import generic

import geocoder
from django_countries.fields import Country
from el_pagination.views import AjaxListView

from core.auth import SUPERVISOR, AuthMixin
from maps import SRID
from maps.utils import bufferize_country_boundaries

from ..models import LocationConfidence, Place, TravelAdvice
from ..utils import geocode


class PlaceListView(generic.ListView):
    model = Place


class PlacePaginatedListView(AjaxListView):
    model = Place


class PlaceStaffListView(AuthMixin, PlaceListView):
    """
    A place for supervisors to see an overview of and manage hosts in their
    area of responsibility.
    """
    template_name = "hosting/place_list_supervisor.html"
    display_fair_usage_condition = True
    minimum_role = SUPERVISOR

    def dispatch(self, request, *args, **kwargs):
        self.country = Country(kwargs['country_code'])
        kwargs['auth_base'] = self.country
        self.in_book_status = {'0': False, '1': True, None: None}[kwargs['in_book']]
        self.invalid_emails = kwargs['email']
        return super().dispatch(request, *args, **kwargs)

    def get_owner(self, object):
        return None

    def get_location(self, object):
        return object

    def get_queryset(self):
        self.base_qs = self.model.available_objects.filter(country=self.country.code).filter(
            Q(visibility__visible_online_public=True) | Q(in_book=True, visibility__visible_in_book=True)
        )
        self.base_qs = self.base_qs.annotate(
            location_valid=Case(
                When(Q(location__isnull=False) & ~Q(location=Point([])), then=True),
                default=False, output_field=BooleanField()
            ),
            location_inaccurate=Case(
                When(Q(location_valid=True) & Q(location_confidence__lt=LocationConfidence.ACCEPTABLE), then=True),
                default=False, output_field=BooleanField()
            ),
            location_accurate=Case(
                When(Q(location_valid=True) & Q(location_confidence__gte=LocationConfidence.ACCEPTABLE), then=True),
                default=False, output_field=BooleanField()
            ),
        )
        if self.in_book_status is not None:
            narrowing_func = getattr(self.base_qs, 'filter' if self.in_book_status else 'exclude')
            qs = narrowing_func(in_book=True, visibility__visible_in_book=True)
        else:
            qs = self.base_qs
        if self.invalid_emails:
            qs = qs.filter(owner__user__email__startswith=settings.INVALID_PREFIX)
        return (qs.prefetch_related('owner__user', 'owner__phones')
                  .order_by('-confirmed', 'checked', 'owner__last_name'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        in_book_status_filter = Q(in_book=True) & Q(visibility__visible_in_book=True)
        context['in_book_count'] = self.base_qs.filter(in_book_status_filter).count()
        context['not_in_book_count'] = self.base_qs.filter(~in_book_status_filter).count()
        if self.in_book_status is True:
            book_filter = in_book_status_filter
            context['place_count'] = context['in_book_count']
        elif self.in_book_status is False:
            book_filter = ~in_book_status_filter
            context['place_count'] = context['not_in_book_count']
        else:
            book_filter = Q()
            context['place_count'] = context['in_book_count'] + context['not_in_book_count']
        context['checked_count'] = self.base_qs.filter(book_filter, checked=True).count()
        context['confirmed_count'] = self.base_qs.filter(book_filter, confirmed=True).count()
        context['not_confirmed_count'] = context['place_count'] - context['confirmed_count']
        context['invalid_emails_count'] = (
            self.base_qs.filter(owner__user__email__startswith=settings.INVALID_PREFIX).count()
        )

        coords = bufferize_country_boundaries(self.country.code)
        if coords:
            context['country_coordinates'] = json.dumps(coords)

        return context


class SearchView(PlacePaginatedListView):
    queryset = Place.available_objects.filter(visibility__visible_online_public=True, owner__death_date__isnull=True)
    paginate_first_by = 25
    paginate_by = 25
    display_fair_usage_condition = True

    def get(self, request, *args, **kwargs):
        def unwhitespace(val):
            return " ".join(val.split())
        if 'ps_q' in request.GET:
            # Keeping Unicode in URL, replacing space with '+'.
            query = uri_to_iri(quote_plus(unwhitespace(request.GET['ps_q'])))
            params = {'query': query} if query else None
            return HttpResponseRedirect(reverse('search', kwargs=params))
        query = kwargs['query'] or ''  # Avoiding query=None
        self.query = unwhitespace(unquote_plus(query))
        # Exclude places whose owner blocked unauthenticated viewing.
        if not request.user.is_authenticated:
            self.queryset = self.queryset.exclude(owner__pref__public_listing=False)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        most_recent_moniker, most_recent = pgettext("value::plural", "MOST RECENT"), False
        if self.query in (most_recent_moniker, most_recent_moniker.replace(" ", "_")):
            most_recent = True
            self.query = ''

        qs = (
            self.queryset
            .select_related('owner', 'owner__user')
            .defer('address', 'description', 'owner__description')
        )

        self.result = geocode(self.query)
        if self.query and self.result.point:
            if any([self.result.country and not self.result.country_code, self.result.state, self.result.city]):
                return (qs
                        .annotate(distance=Distance('location', self.result.point))
                        .order_by('distance'))
            elif self.result.country:  # We assume it's a country
                self.paginate_first_by = 50
                self.paginate_orphans = 5
                self.country_search = True
                return (qs
                        .filter(country=self.result.country_code.upper())
                        .order_by('-owner__user__last_login', '-id'))
        position = geocoder.ip(self.request.META['HTTP_X_REAL_IP']
                               if settings.ENVIRONMENT != 'DEV'
                               else "188.166.58.162")
        position.point = Point(position.xy, srid=SRID) if position.xy else None
        logging.getLogger('PasportaServo.geo').debug(
            "User's position: %s, %s",
            position.address if position.ok and position.address else "UNKNOWN",
            position.xy if position.ok else position.error
        )
        if position.point and not most_recent:
            # Results are sorted by distance from user's current location, but probably
            # it is better not to creep users out by unexpectedly using their location.
            qs = qs.annotate(internal_distance=Distance('location', position.point)).order_by('internal_distance')
        else:
            qs = qs.order_by('-owner__user__last_login', '-id')
        return qs

    def get_detail_queryset(self):
        if len(self.query) <= 3:
            return self.queryset
        lookup = (
            Q()
            | Q(owner__user__username__icontains=self.query)
            | Q(owner__first_name__icontains=self.query)
            | Q(owner__last_name__icontains=self.query)
            | Q(closest_city__icontains=self.query)
        )
        return self.queryset.filter(lookup).select_related('owner__user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if getattr(self, 'country_search', False) and hasattr(self, 'result') and self.result.country_code:
            context['country_advisories'] = TravelAdvice.get_for_country(self.result.country_code.upper())
        return context
