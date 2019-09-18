from django.conf.urls import include, url
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from django.views.generic import RedirectView

from .views import (
    AboutView, FaqView, PrivacyPolicyView,
    SupervisorsView, TermsAndConditionsView,
)

urlpatterns = [
    url(_(r'^about/$'), AboutView.as_view(), name='about'),
    url(_(r'^terms-and-conditions/$'), TermsAndConditionsView.as_view(), name='terms_conditions'),
    url(_(r'^privacy/$'), PrivacyPolicyView.as_view(), name='privacy_policy'),
    url(_(r'^faq/$'), FaqView.as_view(), name='faq'),
    url(_(r'^sv/'), include([
        url(format_lazy(r'^(?:{book}\:(?P<in_book>1)/)?$', book=pgettext_lazy("URL", 'book')),
            SupervisorsView.as_view(), name='supervisors'),
    ])),
    url(_(r'^supervisors/$'), RedirectView.as_view(pattern_name='supervisors')),
]
