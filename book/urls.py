from django.urls import path

from .views import ContactExportView

urlpatterns = [
    path('eksporti/gastigantoj.csv', ContactExportView.as_view(), name='contact_export'),
]
