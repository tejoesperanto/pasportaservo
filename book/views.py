from django.views.generic import TemplateView

from djappypod.response import OdtTemplateResponse

from hosting.models import Place


class DataHolder():
    pass

class Book(TemplateView):
    response_class = OdtTemplateResponse
    template_name = "book/template.odt"


    def get_data(self):
        listX = []
        for x in range(10): #Or whatever your cycle is
            groupX = DataHolder()
            groupX.id = x
            groupX.name = 'SomeData'
            listX.append(groupX)

        for i in listX:
            groupY = DataHolder()
            groupY.detail = 'More data Data'
            groupY.detailList = ['orange','banana','lemons','etc']
            i.groupY = groupY

        return listX

    def get_context_data(self, **context):
        context['title'] = 'Simple as hello ;)'
        context['liste'] = ['a', 'b', 'c']
        places = Place.objects.filter(owner__last_name__istartswith="da")
        countries = set(pl.country for pl in places)
        context['countries'] = countries
        context['places'] = places
        context['listX'] = self.get_data()
        return context

book = Book.as_view()
