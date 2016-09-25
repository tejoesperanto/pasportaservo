from django.conf.urls import url

from .views import pdf_book, contact_export

urlpatterns = [
    url(r'^libro\.pdf$', pdf_book, name='pdf_book'),
    url(r'^gastigantoj\.csv$', contact_export, name='contact_export'),
]
