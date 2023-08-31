from typing import Optional, TypeVar
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils.functional import Promise
from django.views import View

from bs4 import BeautifulSoup
from django_webtest import DjangoTestApp, WebTest
from pyquery import PyQuery

from ...factories import UserFactory

Page = TypeVar('Page', bound='PageTemplate')


class PageTemplate:
    # To be overridden in extending Page classes.
    view_class: type[View]
    url: Promise
    explicit_url = {
        'en': '',
        'eo': '',
    }
    template = ''

    # Common attributes for the views.
    title = {
        'en': "Find accommodation | Pasporta Servo",
        'eo': "Trovu loĝejon | Pasporta Servo",
    }
    header_logged_out = {
        'en': {
            'session': {'text': "log in", 'url': '/login/'},
            'profile': {'text': "register", 'url': '/register/'},
            'use_notice': "For personal use",
        },
        'eo': {
            'session': {'text': "ensaluti", 'url': '/ensaluti/'},
            'profile': {'text': "registriĝi", 'url': '/registrado/'},
            'use_notice': "Por persona uzo",
        },
    }
    header_logged_in = {
        'en': {
            'session': {
                'text': "log out",
                'url': '/logout/'},
            'profile': {
                'text': "My profile",
                'url': {True: '/profile/', False: '/profile/create/'}},
            'settings': {
                'text': "settings",
                'url': {True: '/profile/.../settings/', False: '/account/settings/'}},
            'inbox': {
                'text': "inbox",
                'url': '/messages/inbox/'},
            'use_notice': "For personal use of ",
        },
        'eo': {
            'session': {
                'text': "elsaluti",
                'url': '/elsaluti/'},
            'profile': {
                'text': "Mia profilo",
                'url': {True: '/profilo/', False: '/profilo/krei/'}},
            'settings': {
                'text': "agordoj",
                'url': {True: '/profilo/.../agordoj/', False: '/konto/agordoj/'}},
            'inbox': {
                'text': "poŝtkesto",
                'url': '/leteroj/kesto/'},
            'use_notice': "Por persona uzo de ",
        },
    }
    use_notice = False

    # Private fields.
    _page: DjangoTestApp.response_class

    @classmethod
    def open(
            cls: type[Page],
            test_case: WebTest,
            user: Optional[AbstractUser | UserFactory] = None,
            status: str | int = 200,
            redirect_to: Optional[str] = None,
    ) -> Page:
        page_instance = cls()
        if user is None:
            test_case.app.reset()
        complete_url = f'{cls.url}'
        if redirect_to is not None:
            complete_url += '?' + urlencode({settings.REDIRECT_FIELD_NAME: redirect_to})
        page_instance._page = test_case.app.get(complete_url, status=status, user=user)
        return page_instance

    @property
    def response(self):
        if not hasattr(self, '_page'):
            raise AttributeError("Page was not successfully loaded yet")
        return self._page

    @property
    def html(self) -> BeautifulSoup:
        """
        Returns the response as a `BeautifulSoup` object.
        """
        return self.response.html

    @property
    def pyquery(self) -> PyQuery:
        """
        Returns the response as a `PyQuery` object.
        """
        return self.response.pyquery

    def get_nav_element(self, nav_part: str) -> PyQuery:
        if not hasattr(self, '_header_element'):
            self._header_element = self.pyquery("header")
        return self._header_element.find(f".nav-{nav_part}")

    def get_header_links(self, only_visible: bool = True) -> PyQuery:
        elements = self.pyquery("header a[href]")
        if only_visible:
            elements = elements.not_(".sr-only")
        return elements

    def get_use_notice_text(self) -> str:
        return self.pyquery("header .use-notice").text()

    def get_footer_element(self, footer_part: str) -> PyQuery:
        if not hasattr(self, '_footer_element'):
            self._footer_element = self.pyquery("footer")
        if footer_part == 'env-info':
            return self._footer_element.find(f".{footer_part}")
        else:
            return self._footer_element.find(f"a[href='{reverse(footer_part)}']")
