from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _

from .views import unique_link, confirmed, already_confirmed

urlpatterns = [
    url(_(r'^link/(?P<token>[\w\.\-_]+)$'), unique_link, name='unique_link'),
    url(_(r'^confirmed$'), confirmed, name='confirmed'),
    url(_(r'^already_confirmed$'), already_confirmed, name='already_confirmed'),
]
