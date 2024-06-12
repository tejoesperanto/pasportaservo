from typing import cast

from django.urls import reverse_lazy

from lxml.html import HtmlElement
from pyquery import PyQuery

from core.forms import UserAuthenticationForm, UserRegistrationForm
from core.views import AccountSettingsView, LoginView, RegisterView

from .base import PageTemplate, PageWithFormTemplate


class RegisterPage(PageWithFormTemplate):
    view_class = RegisterView
    form_class = UserRegistrationForm
    url = reverse_lazy('register')
    explicit_url = {
        'en': '/register/',
        'eo': '/registrado/',
    }
    template = 'registration/register.html'
    title = {
        'en': "Register & Find accommodation | Pasporta Servo",
        'eo': "Registriĝu & Trovu loĝejon | Pasporta Servo",
    }
    redirects_unauthenticated = False
    redirects_logged_in = True
    form = {
        'selector': ".register",
        'title': {
            'en': "New Account",
            'eo': "Nova Konto",
        },
    }


class LoginPage(PageWithFormTemplate):
    view_class = LoginView
    form_class = UserAuthenticationForm
    url = reverse_lazy('login')
    explicit_url = {
        'en': '/login/',
        'eo': '/ensaluti/',
    }
    template = 'registration/login.html'
    title = {
        'en': "Log in & Find accommodation | Pasporta Servo",
        'eo': "Ensalutu & Trovu loĝejon | Pasporta Servo",
    }
    redirects_unauthenticated = False
    redirects_logged_in = True
    form = {
        'selector': ".login",
        'title': {
            'en': "Log In",
            'eo': "Ensaluto",
        },
    }


class AccountSettingsPage(PageTemplate):
    view_class = AccountSettingsView
    url = reverse_lazy('account_settings')
    explicit_url = {
        'en': '/account/settings/',
        'eo': '/konto/agordoj/',
    }
    template = 'account/settings.html'
    title = {
        'en': "Settings | Pasporta Servo",
        'eo': "Agordoj | Pasporta Servo",
    }
    use_notice = True

    def get_heading_text(self) -> str:
        return cast(str, self.pyquery("[role='main'] > h2").text())

    def get_sections(self) -> PyQuery:
        return self.pyquery("section.callout")

    def get_section_by_heading(self, heading: str) -> PyQuery:
        return self.pyquery("section.callout").filter(
            lambda i, this: PyQuery(this).children("h4").eq(0).text() == heading
        )

    def get_section_heading(self, section_element: PyQuery | HtmlElement) -> str:
        return cast(str, PyQuery(section_element).children("h4").eq(0).text())

    def get_section_color(self, section_element: PyQuery | HtmlElement) -> str:
        css_classes = cast(str, PyQuery(section_element).attr("class") or "")
        css_classes = [cls for cls in css_classes.split() if cls.startswith("callout-")]
        if css_classes:
            return css_classes[0].replace("callout-", "")
        else:
            return ""
