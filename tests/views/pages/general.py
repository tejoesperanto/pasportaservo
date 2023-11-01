from typing import cast

from django.conf import settings
from django.urls import reverse_lazy
from django.utils.functional import classproperty
from django.views.generic import TemplateView

from pyquery import PyQuery

from core.views import HomeView
from pages.views import AboutView

from .base import PageTemplate


class HomePage(PageTemplate):
    view_class = HomeView
    url = reverse_lazy('home')
    explicit_url = {
        'en': '/',
        'eo': '/',
    }
    template = 'core/home.html'
    redirects_unauthenticated = False

    def get_headings(self) -> PyQuery:
        return self.pyquery("[role='heading']")

    def get_hero_content(self) -> PyQuery:
        return self.pyquery("header .search-container")


class OkayPage(PageTemplate):
    view_class = TemplateView
    explicit_url = {
        'en': '/ok',
        'eo': r'/%C4%89u',
    }
    template = '200.html'
    redirects_unauthenticated = False

    @classproperty
    def url(cls):
        return cls.explicit_url[settings.LANGUAGE_CODE]

    def get_headings(self) -> PyQuery:
        return self.pyquery("[role='heading']")

    def get_hero_content(self) -> PyQuery:
        return self.pyquery("header .search-container")


class AboutPage(PageTemplate):
    view_class = AboutView
    url = reverse_lazy('about')
    explicit_url = {
        'en': '/about/',
        'eo': '/pri-ni/',
    }
    template = 'pages/about.html'
    title = {
        # The base page "about us" is always in Esperanto.
        'en': "Internacia gastiga servo per Esperanto : Pasporta Servo",
        'eo': "Internacia gastiga servo per Esperanto : Pasporta Servo",
    }
    redirects_unauthenticated = False

    def get_heading_text(self) -> str:
        return cast(str, self.pyquery("[role='main'] > h1").text())

    def get_attribution(self) -> PyQuery:
        return self.pyquery("[role='main'] .attribution")
