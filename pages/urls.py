from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _

from .views import about, terms_conditions, supervisors, faq

urlpatterns = [
    url(_(r'^about/$'), about, name='about'),
    url(_(r'^terms-and-conditions/$'), terms_conditions, name='terms_conditions'),
    url(_(r'^supervisors/$'), supervisors, name='supervisors'),
    url(_(r'^faq/$'), faq, name='faq'),
]
