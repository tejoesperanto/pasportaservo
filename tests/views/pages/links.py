from django.urls import reverse_lazy
from django.utils.functional import classproperty
from django.views.generic import TemplateView

from pyquery import PyQuery

from links.utils import create_unique_url
from links.views import AlreadyConfirmedView, ConfirmedView

from .base import PageHeroTemplate, PageTemplate


class LinkInvalidPage(PageHeroTemplate):
    view_class = TemplateView
    template = 'links/invalid_link.html'
    redirects_unauthenticated = False
    content_title: PageHeroTemplate._LocalizationSpec[str] = {
        'en': "Invalid Link",
        'eo': "Malbona ligilo",
    }
    content_subtitle: PageHeroTemplate._LocalizationSpec[dict[str, str]] = {
        'en': {
            'heading': "The link is not valid",
            'details': "",
        },
        'eo': {
            'heading': "La ligilo havas malbonan formon aŭ malĝustan konfirmo-ĵetonon.",
            'details': "",
        },
    }

    @classproperty
    def url(cls):
        value = create_unique_url({})
        return value[0]

    @classproperty
    def explicit_url(cls):
        value = create_unique_url({})
        token = value[1]
        return {'en': f'/link/{token}', 'eo': f'/ligilo/{token}'}


class LinkExpiredSignaturePage(LinkInvalidPage):
    template = 'links/signature_expired.html'
    content_subtitle = {
        'en': {
            'heading': "Signature Expired",
            'details': "The link is not valid anymore",
        },
        'eo': {
            'heading': "Tempostampo ne plu validas",
            'details': (
                "La ligilo estis kreita antaŭ tro da tempo kaj ĝi ne plu validas."
                " Vi bezonas novan ligilon."
            ),
        },
    }


class LinkBadTimeSignaturePage(LinkInvalidPage):
    template = 'links/bad_time_signature.html'
    content_subtitle = {
        'en': {
            'heading': "Bad Time Signature; The link seems not valid",
            'details': "",
        },
        'eo': {
            'heading': "Malbona tempostampo; La ligilo ne ŝajnas esti valida plu.",
            'details': "",
        },
    }


class LinkBadSignaturePage(LinkInvalidPage):
    pass


class InfoConfirmedPage(PageTemplate):
    view_class = ConfirmedView
    url = reverse_lazy('info_confirmed')
    explicit_url = {
        'en': '/current/confirmed/',
        'eo': '/aktualigo/konfirmita/',
    }
    template = 'links/confirmed.html'
    title = {
        'en': "Data confirmed at Pasporta Servo",
        'eo': "Informoj konfirmitaj ĉe Pasporta Servo",
    }
    content = {
        'en': {
            'h1': "Data confirmed",
            'h3': "You just confirmed that your profile and address are up-to-date. Thanks!",
        },
        'eo': {
            'h1': "Informoj konfirmitaj",
            'h3': "Vi ĵus konfirmis ke viaj profilo kaj adreso estas aktualaj. Dankon!",
        }
    }
    redirects_unauthenticated = False

    def get_headings(self) -> PyQuery:
        return self.pyquery(":header")


class InfoAlreadyConfirmedPage(PageTemplate):
    view_class = AlreadyConfirmedView
    url = reverse_lazy('info_already_confirmed')
    explicit_url = {
        'en': '/current/already_confirmed/',
        'eo': '/aktualigo/jam_konfirmita/',
    }
    template = 'links/already_confirmed.html'
    title = {
        'en': "Data confirmed at Pasporta Servo",
        'eo': "Informoj konfirmitaj ĉe Pasporta Servo",
    }
    content = {
        'en': {
            'h1': "Already confirmed",
            'h3': "You already confirmed the accuracy of your profile and address. Thanks!",
        },
        'eo': {
            'h1': "Informoj jam konfirmitaj",
            'h3': "Vi jam konfirmis la aktualecon de viaj profilo kaj adreso. Dankon!",
        }
    }
    redirects_unauthenticated = False

    def get_headings(self) -> PyQuery:
        return self.pyquery(":header")
