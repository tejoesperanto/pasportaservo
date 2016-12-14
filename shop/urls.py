from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _

from .views import ReserveRedirectView, ReserveView, ReservationView


urlpatterns = [
    url(_(r'^reserve/$'),
        ReserveRedirectView.as_view(), name='reserve'),
    url(_(r'^reserve/(?P<product_code>\w+)/$'),
        ReserveView.as_view(), name='reserve'),
    url(_(r'^reservation/(?P<product_code>\w+)/$'),
        ReservationView.as_view(), name='reservation'),
]
