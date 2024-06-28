from threading import Lock
from typing import Optional, TypedDict, TypeVar, cast

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.forms import Form, ModelForm
from django.urls import reverse
from django.utils.functional import Promise
from django.views import View

from bs4 import BeautifulSoup
from django_webtest import DjangoTestApp, WebTest
from pyquery import PyQuery

from ...factories import UserFactory

Page = TypeVar('Page', bound='PageTemplate')
PageWithForm = TypeVar('PageWithForm', bound='PageWithFormTemplate')


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
    redirects_unauthenticated = True
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
            'use_notice': {True: "For personal use of ", False: "For personal use"},
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
            'use_notice': {True: "Por persona uzo de ", False: "Por persona uzo"},
        },
    }
    redirects_logged_in = False
    use_notice = False

    # Private Page instance fields.
    _test_case: WebTest
    _page: DjangoTestApp.response_class
    _open_pages: dict[str | None, 'PageTemplate'] = {}
    _open_pages_lock = Lock()

    @classmethod
    def open(
            cls: type[Page],
            test_case: WebTest,
            user: Optional[AbstractUser | UserFactory] = None,
            status: str | int = 200,
            redirect_to: Optional[str] = None,
            extra_params: Optional[dict[str, str | int | Promise]] = None,
            extra_headers: Optional[dict[str, str]] = None,
            reuse_for_lang: Optional[str] = None,
    ) -> Page:
        if reuse_for_lang and not (extra_params or extra_headers):
            this_page_key = (
                f'{cls.__name__}.{reuse_for_lang}'
                f'.{getattr(user, "pk", None)}.{hash(redirect_to)}'
            )
            cls._open_pages_lock.acquire()
            open_page_instance = cls._open_pages.get(this_page_key)
            cls._open_pages_lock.release()
            if open_page_instance:
                return cast(Page, open_page_instance)
        else:
            this_page_key = None

        page_instance = cls()
        page_instance._test_case = test_case
        if user is None:
            test_case.app.reset()
        extra_params = extra_params or {}
        if redirect_to is not None:
            extra_params.update({settings.REDIRECT_FIELD_NAME: redirect_to})
        page_instance._page = test_case.app.get(
            str(cls.url), params=extra_params, headers=extra_headers,
            status=status, user=user,
        )

        if reuse_for_lang:
            cls._open_pages_lock.acquire()
            cls._open_pages[this_page_key] = page_instance
            cls._open_pages_lock.release()
        return page_instance

    @classmethod
    def wrap_response(
            cls: type[Page],
            test_case: WebTest,
            response: DjangoTestApp.response_class,
    ) -> Page:
        page_instance = cls()
        page_instance._test_case = test_case
        page_instance._page = response
        return page_instance

    def follow(self, *, once=False, **kwargs):
        """
        If this page is a redirect, follow that redirect and others.
        It is an error to try following a page which is not a redirect response.
        If `once` is True, only the first level of redirection is followed.
        Any other keyword arguments are passed to `webtest.app.TestApp.get`.
        """
        if not (300 <= self.response.status_code < 400):
            raise AssertionError(
                f"Only redirect responses can be followed (not {self.response.status})"
            )
        if once:
            self._page = self.response.follow(**kwargs)
        else:
            self._page = self.response.maybe_follow(**kwargs)

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

    def get_user(self) -> AbstractUser | None:
        context = getattr(self.response, 'context', None) or {}
        return context.get('user')

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
        return cast(str, self.pyquery("header .use-notice").text())

    Messages = TypedDict('Messages', {'content': list[str], 'level': list[str | None]})

    def get_toplevel_messages(self) -> Messages:
        result = self.Messages({
            'content': [],
            'level': [],
        })
        for message_element in self.pyquery("section.messages > .message"):
            message_element = PyQuery(message_element)
            result['content'].append(message_element.children('span[id]').html())
            result['level'].append(message_element.attr('data-level'))
        return result

    def get_footer_element(self, footer_part: str) -> PyQuery:
        if not hasattr(self, '_footer_element'):
            self._footer_element = self.pyquery("footer")
        if footer_part == 'env-info':
            return self._footer_element.find(f".{footer_part}")
        else:
            return self._footer_element.find(f"a[href='{reverse(footer_part)}']")


class PageWithFormTemplate(PageTemplate):
    class _RenderedFormDefinitionBase(TypedDict):
        selector: str
        title: dict[str, str]

    class RenderedFormDefinition(_RenderedFormDefinitionBase, total=False):
        object: Form | ModelForm | None

    form_class: type[Form] | type[ModelForm]
    form: RenderedFormDefinition = {
        'selector': "",
        'title': {
            'en': "", 'eo': "",
        },
    }

    @classmethod
    def open(cls: type[PageWithForm], *args, **kwargs) -> PageWithForm:
        page_instance = super().open(*args, **kwargs)
        page_instance.form['object'] = (page_instance.response.context or {}).get('form')
        return page_instance

    def submit(
            self,
            form_data: dict,
            redirect_to: Optional[str] = None,
            csrf_token: Optional[str] = None,
    ):
        extra_form_data = {
            'csrfmiddlewaretoken': csrf_token or (self.response.context or {}).get('csrf_token'),
        }
        if redirect_to:
            extra_form_data[settings.REDIRECT_FIELD_NAME] = redirect_to
        self._page = self._test_case.app.post(
            self.url,
            {**form_data, **extra_form_data},
            status='*')
        if getattr(self._page, 'context', None) and 'form' in self._page.context:
            self.form['object'] = self._page.context['form']

    def get_form(self) -> PyQuery:
        if not hasattr(self, '_form_element'):
            self._form_element = self.pyquery(f".base-form{self.form['selector']}")
        return self._form_element

    def get_form_title(self) -> str:
        return cast(str, self.get_form().children("h4").text())

    def get_form_element(self, selector: str) -> PyQuery:
        return self.get_form().find(f"form {selector}")

    def get_form_errors(self, field_name: Optional[str] = None) -> str | list[str]:
        if field_name is None:
            return self.get_form().find("form > * > .alert").text()
        else:
            single_control_errors = self.get_form().find(
                f"form > * .form-control[name='{field_name}'] ~ [id^='error_']")
            input_group_errors = self.get_form().find(
                f"form > * .input-group:has(\".form-control[name='{field_name}']\")"
                + " ~ [id^='error_']")
            return [
                cast(str, PyQuery(error_element).text())
                for error_element in
                single_control_errors.extend(input_group_errors)
            ]


class PageWithTitleHeadingTemplate(PageTemplate):
    page_title: str | dict[str, str]

    def get_heading_text(self) -> str:
        return cast(str, self.pyquery("[role='main'] > h1").text())
