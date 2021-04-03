from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy
from django.views import generic

from django_countries.fields import Country

from core.auth import PERM_SUPERVISOR
from core.mixins import flatpages_as_templates
from core.models import Policy
from core.utils import sort_by
from hosting.models import Place, Profile


class AboutView(generic.TemplateView):
    template_name = 'pages/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_places = Place.available_objects.filter(visibility__visible_online_public=True)
        context['num_of_hosts'] = all_places.values('owner').distinct().count()
        context['num_of_countries'] = all_places.values('country').distinct().count()
        context['num_of_cities'] = all_places.values('city').distinct().count()
        return context


class TermsAndConditionsView(generic.TemplateView):
    template_name = 'pages/terms_conditions.html'


@flatpages_as_templates
class PrivacyPolicyView(generic.TemplateView):
    template_name = 'pages/privacy.html'
    standalone_policy_view = True

    def get(self, request, *args, **kwargs):
        try:
            self._policy = Policy.objects.order_by('-id').values('content')[0]
        except IndexError as ierr:
            raise RuntimeError("Service misconfigured: No privacy policy is defined.") from ierr
        return super().get(request, *args, **kwargs)

    @cached_property
    def policy_content(self):
        return self.render_flat_page(self._policy)

    @cached_property
    def effective_date(self):
        return Policy.get_effective_date_for_policy(self._policy['content'])


class SupervisorsView(generic.TemplateView):
    template_name = 'pages/supervisors.html'
    book_codes = {False: '0', True: '1', None: None}

    def dispatch(self, request, *args, **kwargs):
        # Extract the 'places appearing in book' query param code from URL
        # and convert back to a True/False status.
        code_from_kwarg = {v: k for k, v in self.book_codes.items()}
        code_from_kwarg.update({None: False})
        self.in_book_query = code_from_kwarg[kwargs['in_book']]
        if self.in_book_query and not request.user.has_perm(PERM_SUPERVISOR):
            # The 'by book status' view is only available to supervisors.
            return HttpResponseRedirect(format_lazy(
                "{supervisors_url}#{section_countries}",
                supervisors_url=reverse_lazy('supervisors'),
                section_countries=pgettext_lazy("URL", "countries-list"),
            ))
        return super().dispatch(request, *args, **kwargs)

    @cached_property
    def supervisors_per_country(self):
        """
        Loads the profiles of all supervisors and returns a dictionary linking
        country codes to these profiles (without duplicating objects).
        """
        # First, obtain the profile IDs of active supervisors for all places marked as 'available',
        # coupled with the group name (country code):
        # [{'id': 10, 'user__groups__name': 'CA'},
        #  {'id': 38, 'user__groups__name': 'NZ'},
        #  {'id': 10, 'user__groups__name': 'NZ'}]
        all_supervisors = Profile.objects_raw.filter(
            user__is_active=True,
            user__groups__name__in=(
                Place.objects_raw.filter(available=True).values_list('country', flat=True).distinct()
            )
        )
        per_country = all_supervisors.values('id', 'user__groups__name')

        # Convert the list into a dictionary with keys = country codes, and values = sets of
        # supervisor profile IDs:  {'CA': {10}, 'NZ: {38, 10}}
        supervisors_per_country = {
            country_code: set(
                sv['id'] for sv in per_country if sv['user__groups__name'] == country_code
            )
            for country_code in set(sv['user__groups__name'] for sv in per_country)
        }
        # Load basic information about each supervisor from DB; for convenience, the profiles
        # are indexed by their ID. Full models are needed, though, to make use of the methods
        # defined on the Profile model.
        supervisor_profiles = {
            profile.pk: profile
            for profile in
            Profile.objects_raw
            .filter(id__in=map(lambda sv: sv['id'], per_country))
            .only('first_name', 'last_name', 'names_inversed')
        }
        # Replace the raw IDs in the dict by actual profile models.
        for country_code, supervisors in supervisors_per_country.items():
            supervisors_per_country[country_code] = [supervisor_profiles[pk] for pk in supervisors]
        return supervisors_per_country

    def get_countries(self, filter_for_book=False, filter_for_supervisor=False):
        """
        Calculates the counts and the supervisors for each country.
        """
        book_filter = Q(in_book=True, visibility__visible_in_book=True)
        online_filter = Q(visibility__visible_online_public=True)
        counts_filtered = {
            'place_count': Count('pk'),
            'checked_count': Count('pk', filter=Q(checked=True)),
            'only_confirmed_count': Count('pk', filter=Q(confirmed=True, checked=False)),
        }
        place_counts = (
            Place.available_objects
            .filter(
                book_filter if filter_for_book else
                ((book_filter | online_filter) if filter_for_supervisor else online_filter)
            )
            # QuerySet.values(...).annotate(...).order_by() performs a GROUP BY query,
            # removing the default ordering fields of the model, if any.
            .select_related(None).values('country')
            .annotate(**counts_filtered)
            .order_by()
        )

        # Sort the countries by their name and enrich with information about supervisors
        # and total number of available places, as well as count of confirmed (by owners)
        # and checked (by supervisors) places.
        countries = sort_by(['name'], {Country(p['country']) for p in place_counts})
        for country in countries:
            try:
                country.supervisors = sorted(self.supervisors_per_country[country.code])
            except KeyError:
                pass
            counts_for_country = next(filter(lambda p: p['country'] == country, place_counts))
            for count_name in counts_filtered:
                setattr(country, count_name, counts_for_country[count_name])
        return countries

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_supervisor = self.request.user.has_perm(PERM_SUPERVISOR)
        context['countries'] = {'available': {
            'active': not self.in_book_query,
            'in_book': self.book_codes[None],
            'data': self.get_countries(filter_for_supervisor=is_supervisor)
        }}
        if is_supervisor:
            context['countries'].update({'in_book': {
                'active': self.in_book_query,
                'in_book': self.book_codes[True],
                'data': self.get_countries(filter_for_book=True, filter_for_supervisor=True)
            }})
        return context


class FaqView(generic.TemplateView):
    template_name = 'pages/faq.html'
