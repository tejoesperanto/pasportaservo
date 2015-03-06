from django.views.generic import TemplateView

from djappypod.response import OdtTemplateResponse

from hosting.models import Place


class YourDocument(TemplateView):
    response_class = OdtTemplateResponse
    template_name = "book/template.odt"

    def get_context_data(self, **context):
        context['title'] = 'Simple as hello ;)'
        context['liste'] = ['a', 'b', 'c']
        places = Place.objects.filter(owner__last_name__istartswith="da")
        countries = set(pl.country for pl in places)
        context['countries'] = countries
        context['places'] = places
        return context

doc = YourDocument.as_view()
