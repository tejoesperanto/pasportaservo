from django.views import generic
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.text import format_lazy

from core.auth import PERM_SUPERVISOR
from hosting.models import Place
from hosting.utils import sort_by_name
from django.utils.translation import pgettext_lazy, ugettext_lazy as _


class AboutView(generic.TemplateView):
    template_name = 'pages/about.html'

about = AboutView.as_view()


class TermsAndConditionsView(generic.TemplateView):
    template_name = 'pages/terms_conditions.html'

terms_conditions = TermsAndConditionsView.as_view()


class SupervisorsView(generic.TemplateView):
    template_name = 'pages/supervisors.html'
    book_codes = {False: '0', True: '1', None: None}

    def dispatch(self, request, *args, **kwargs):
        code_from_kwarg = {v: k for k, v in self.book_codes.items()}
        code_from_kwarg.update({None: False})
        self.in_book = code_from_kwarg[kwargs['in_book']]
        if self.in_book and not request.user.has_perm(PERM_SUPERVISOR):
            return HttpResponseRedirect(format_lazy("{supervisors_url}#{section_countries}",
                supervisors_url=reverse_lazy('supervisors'),
                section_countries=pgettext_lazy("URL", "countries-list"))
            )
        return super().dispatch(request, *args, **kwargs)

    def get_countries(self, filter_for_book=False):
        places = Place.available_objects.all()
        if filter_for_book:
            places = places.filter(in_book=True)
        groups = Group.objects.exclude(user=None)
        countries = sort_by_name({p.country for p in places})
        for country in countries:
            try:
                group = groups.get(name=country.code)
                country.supervisors = sorted(user.profile for user in group.user_set.all() if hasattr(user, 'profile'))
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
        context['countries'] = {'available': {
            'active': not self.in_book, 'in_book': self.book_codes[None], 'data': self.get_countries()
        }}
        if self.request.user.has_perm(PERM_SUPERVISOR):
            context['countries'].update({'in_book': {
                'active': self.in_book, 'in_book': self.book_codes[True], 'data': self.get_countries(True)
            }})
        return context

supervisors = SupervisorsView.as_view()


class FaqView(generic.TemplateView):
    template_name = 'pages/faq.html'

faq = FaqView.as_view()
