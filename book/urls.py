from django.conf.urls import url

from .views import pdf_book

urlpatterns = [
    url(r'^book\.pdf$', pdf_book, name='pdf_book')
]
