from django.conf.urls import include, url
from django.utils.translation import ugettext_lazy as _

from .views import UniqueLinkView, ConfirmedView, AlreadyConfirmedView

urlpatterns = [
    url(_(r'^link/(?P<token>[\w\.\-_]+)$'), UniqueLinkView.as_view(), name='unique_link'),
    url(_(r'^current/'), include([
        url(_(r'^confirmed/$'), ConfirmedView.as_view(), name='info_confirmed'),
        url(_(r'^already_confirmed/$'), AlreadyConfirmedView.as_view(), name='info_already_confirmed'),
    ])),
]
