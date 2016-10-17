from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _

from .views import unique_link, info_confirmed, info_already_confirmed

urlpatterns = [
    url(_(r'^link/(?P<token>[\w\.\-_]+)$'), unique_link, name='unique_link'),
    url(_(r'^current/confirmed/$'), info_confirmed, name='info_confirmed'),
    url(_(r'^current/already_confirmed/$'), info_already_confirmed, name='info_already_confirmed'),
]
