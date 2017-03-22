from django.conf.urls import url

from .views import contact_export

urlpatterns = [
    url(r'^gastigantoj\.csv$', contact_export, name='contact_export'),
]
