from django.conf.urls import url

from .views import ContactExportView

urlpatterns = [
    url(r'^eksporti/gastigantoj\.csv$', ContactExportView.as_view(), name='contact_export'),
]
