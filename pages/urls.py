from django.urls import include, path, re_path
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy
from django.views.generic import RedirectView

from .views import (
    AboutView, FaqView, PrivacyPolicyView,
    SupervisorsView, TermsAndConditionsView,
)

urlpatterns = [
    path(
        pgettext_lazy("URL", 'about/'),
        AboutView.as_view(), name='about'),
    path(
        pgettext_lazy("URL", 'terms-and-conditions/'),
        TermsAndConditionsView.as_view(), name='terms_conditions'),
    path(
        pgettext_lazy("URL", 'privacy/'), include([
            path(
                '', PrivacyPolicyView.as_view(), name='privacy_policy'),
            path(
                format_lazy(
                    '{policy}:<slug:policy_version>/',
                    policy=pgettext_lazy("URL", 'policy')),
                PrivacyPolicyView.as_view(), name='privacy_policy_version'),
        ])),
    path(
        pgettext_lazy("URL", 'faq/'),
        FaqView.as_view(), name='faq'),
    path(
        pgettext_lazy("URL", 'sv/'), include([
            re_path(
                format_lazy(
                    r'^(?:{book}\:(?P<in_book>1)/)?$',
                    book=pgettext_lazy("URL", 'book')),
                SupervisorsView.as_view(), name='supervisors'),
        ])),
    path(
        pgettext_lazy("URL", 'supervisors/'),
        RedirectView.as_view(pattern_name='supervisors')),
]
