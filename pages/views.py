from django.contrib.auth.models import Group
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy
from django.views import generic

from core.auth import PERM_SUPERVISOR
from core.mixins import flatpages_as_templates
from core.models import Policy
from core.utils import sort_by
from hosting.models import Place


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
        code_from_kwarg = {v: k for k, v in self.book_codes.items()}
        code_from_kwarg.update({None: False})
        self.in_book_status = code_from_kwarg[kwargs['in_book']]
        if self.in_book_status and not request.user.has_perm(PERM_SUPERVISOR):
            return HttpResponseRedirect(format_lazy(
                "{supervisors_url}#{section_countries}",
                supervisors_url=reverse_lazy('supervisors'),
                section_countries=pgettext_lazy("URL", "countries-list"),
            ))
        return super().dispatch(request, *args, **kwargs)

    def get_countries(self, filter_for_book=False, filter_for_supervisor=False):
        book_filter = Q(in_book=True, visibility__visible_in_book=True)
        online_filter = Q(visibility__visible_online_public=True)
        places = Place.available_objects.filter(
            book_filter if filter_for_book else
            ((book_filter | online_filter) if filter_for_supervisor else online_filter)
        )
        groups = Group.objects.exclude(user=None)
        countries = sort_by(["name"], {p.country for p in places})
        for country in countries:
            try:
                group = groups.get(name=country.code)
                country.supervisors = sorted(
                    user.profile for user in group.user_set.filter(
                        is_active=True, profile__isnull=False, profile__deleted_on__isnull=True)
                )
            except Group.DoesNotExist:
                pass
            places_for_country = places.filter(country=country)
            country.place_count = places_for_country.count()
            country.checked_count = places_for_country.filter(checked=True).count()
            country.only_confirmed_count = places_for_country.filter(
                confirmed=True, checked=False).count()
        return countries

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_supervisor = self.request.user.has_perm(PERM_SUPERVISOR)
        context['countries'] = {'available': {
            'active': not self.in_book_status,
            'in_book': self.book_codes[None],
            'data': self.get_countries(filter_for_supervisor=is_supervisor)
        }}
        if is_supervisor:
            context['countries'].update({'in_book': {
                'active': self.in_book_status,
                'in_book': self.book_codes[True],
                'data': self.get_countries(filter_for_book=True, filter_for_supervisor=True)
            }})
        return context


class FaqView(generic.TemplateView):
    template_name = 'pages/faq.html'
