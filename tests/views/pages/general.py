from abc import ABCMeta, abstractmethod

from django.conf import settings
from django.urls import reverse_lazy
from django.utils.functional import classproperty
from django.views.generic import TemplateView

from pyquery import PyQuery

from core.views import HomeView
from pages.views import (
    AboutView, FaqView, PrivacyPolicyView, TermsAndConditionsView,
)

from .base import PageTemplate, PageWithTitleHeadingTemplate


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


class PageWithLanguageSwitcher(PageTemplate, metaclass=ABCMeta):
    @abstractmethod
    def get_lang_switcher(self) -> PyQuery: ...  # noqa: E704

    @abstractmethod
    def get_lang_switcher_label(self) -> PyQuery: ...  # noqa: E704

    @abstractmethod
    def get_lang_switcher_languages(self) -> PyQuery: ...  # noqa: E704

    @abstractmethod
    def is_localized_page(self) -> bool: ...  # noqa: E704

    @property
    @abstractmethod
    def locale(self) -> str: ...  # noqa: E704

    @property
    def base_url_for_localized_page(self):
        return self.url


class AboutPage(PageWithTitleHeadingTemplate, PageWithLanguageSwitcher):
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
    page_title = "Pasporta Servo: Internacia gastiga servo per Esperanto"

    def get_attribution(self) -> PyQuery:
        return self.pyquery("[role='main'] .attribution")

    def get_lang_switcher(self) -> PyQuery:
        return self.pyquery(".language-switcher")

    def get_lang_switcher_label(self) -> PyQuery:
        return self.get_lang_switcher().find("button > b")

    def get_lang_switcher_languages(self) -> PyQuery:
        return self.get_lang_switcher().find("ul > li > a")

    def is_localized_page(self) -> bool:
        return False

    @property
    def locale(self) -> str:
        return settings.LANGUAGE_CODE


class FAQPage(PageWithTitleHeadingTemplate):
    view_class = FaqView
    url = reverse_lazy('faq')
    explicit_url = {
        'en': '/faq/',
        'eo': '/oftaj-demandoj/',
    }
    template = 'pages/faq.html'
    title = {
        # The Questions-and-Answers page is always in Esperanto.
        'en': "Oftaj demandoj | Pasporta Servo",
        'eo': "Oftaj demandoj | Pasporta Servo",
    }
    redirects_unauthenticated = False
    page_title = "Oftaj Demandoj"

    def get_section_headings(self) -> PyQuery:
        return self.pyquery("[role='main'] > section > h3")


class TCPage(PageWithTitleHeadingTemplate):
    view_class = TermsAndConditionsView
    url = reverse_lazy('terms_conditions')
    explicit_url = {
        'en': '/terms-and-conditions/',
        'eo': '/kond/',
    }
    template = 'pages/terms_conditions.html'
    title = {
        'en': "Terms | Pasporta Servo",
        'eo': "Kondiĉoj | Pasporta Servo",
    }
    redirects_unauthenticated = False
    page_title = {
        'en': "Conditions of Usage of Pasporta Servo",
        'eo': "Kondiĉoj por la uzado de Pasporta Servo",
    }

    def get_terms_items(self) -> PyQuery:
        return self.pyquery("[role='main'] > blockquote")

    def get_404_headings(self) -> PyQuery:
        return self.pyquery("[role='heading']")


class PrivacyPage(PageWithTitleHeadingTemplate):
    view_class = PrivacyPolicyView
    url = reverse_lazy('privacy_policy')
    explicit_url = {
        'en': '/privacy/',
        'eo': '/privateco/',
    }
    template = 'pages/privacy.html'
    title = {
        # The Privacy Policy page is always in Esperanto.
        'en': "Politiko pri privateco | Pasporta Servo",
        'eo': "Politiko pri privateco | Pasporta Servo",
    }
    redirects_unauthenticated = False
    page_title = {
        'en': "Policy of Privacy within Pasporta Servo",
        'eo': "Politiko pri privateco ĉe Pasporta Servo",
    }

    def get_effective_date(self) -> PyQuery:
        return self.pyquery("[role='main'] > h1 + h2")

    def get_validity_note(self) -> PyQuery:
        return self.pyquery("#policy-validity-note")

    def get_summary_id(self) -> str:
        return "policy-changes"

    def get_summary(self) -> PyQuery:
        return self.pyquery(f"#{self.get_summary_id()}").parent()

    def get_policy_switcher(self) -> PyQuery:
        return self.pyquery(".policy-switcher")

    def get_policy_swither_label(self, js: bool) -> PyQuery:
        switch_elements = self.get_policy_switcher()
        if js:
            return switch_elements.eq(0).find("button > b")
        else:
            return switch_elements.eq(1).find("label")

    def get_policy_switcher_items(self, js: bool) -> PyQuery:
        switch_elements = self.get_policy_switcher()
        if js:
            return switch_elements.eq(0).find("ul > li > a")
        else:
            return switch_elements.eq(1).find("select > option")

    def get_policy_switcher_submit(self, js: bool) -> PyQuery:
        switch_elements = self.get_policy_switcher()
        if js:
            return switch_elements.eq(0)("")
        else:
            return switch_elements.eq(1).find("[type='submit']")
