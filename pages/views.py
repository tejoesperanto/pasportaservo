from django.views import generic
from django.contrib.auth.models import Group

from hosting.models import Place
from hosting.utils import sort_by_name

class AboutView(generic.TemplateView):
    template_name = 'pages/about.html'

about = AboutView.as_view()


class TermsAndConditionsView(generic.TemplateView):
    template_name = 'pages/terms_conditions.html'

terms_conditions = TermsAndConditionsView.as_view()


class SupervisorsView(generic.TemplateView):
    template_name = 'pages/supervisors.html'

    def countries(self):
        places = Place.available_objects.filter(in_book=True)
        groups = Group.objects.exclude(user=None)
        countries = sort_by_name({p.country for p in places})
        for country in countries:
            try:
                group = groups.get(name=str(country))
                country.supervisors = sorted(user.profile for user in group.user_set.all())
            except Group.DoesNotExist:
                pass
            country.place_count = places.filter(country=country).count()
        return countries

supervisors = SupervisorsView.as_view()


class FaqView(generic.TemplateView):
    template_name = 'pages/faq.html'

faq = FaqView.as_view()
