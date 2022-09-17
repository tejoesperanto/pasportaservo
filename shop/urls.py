from django.urls import include, path
from django.utils.translation import pgettext_lazy

from .views import ReservationView, ReserveRedirectView, ReserveView

urlpatterns = [
    path(
        pgettext_lazy("URL", 'reserve/'), include([
            path('', ReserveRedirectView.as_view(), name='reserve'),
            path('<slug:product_code>/', ReserveView.as_view(), name='reserve'),
        ])),
    path(
        pgettext_lazy("URL", 'reservation/'), include([
            path('<slug:product_code>/', ReservationView.as_view(), name='reservation'),
        ])),
]
