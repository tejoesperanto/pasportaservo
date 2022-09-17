from django.urls import include, path, register_converter
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy

from .views import AlreadyConfirmedView, ConfirmedView, UniqueLinkView


class TokenConverter:
    regex = r'[\w\.\-_]+'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(TokenConverter, 'token')


urlpatterns = [
    path(
        format_lazy('{link}<token:token>', link=pgettext_lazy("URL", 'link/')),
        UniqueLinkView.as_view(), name='unique_link'),
    path(
        pgettext_lazy("URL", 'current/'), include([
            path(
                pgettext_lazy("URL", 'confirmed/'),
                ConfirmedView.as_view(), name='info_confirmed'),
            path(
                pgettext_lazy("URL", 'already_confirmed/'),
                AlreadyConfirmedView.as_view(), name='info_already_confirmed'),
        ])),
]
