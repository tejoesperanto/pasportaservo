from django.conf import settings
from django.urls import reverse_lazy
from django.utils.functional import classproperty
from django.views.generic import TemplateView

from pyquery import PyQuery

from core.views import HomeView

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
