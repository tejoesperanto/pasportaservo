from typing import cast

from django.contrib.auth.views import PasswordResetDoneView
from django.urls import reverse_lazy
from django.utils.translation import pgettext_lazy

from lxml.html import HtmlElement
from pyquery import PyQuery

from core.forms import (
    SystemPasswordResetRequestForm, UserAuthenticationForm,
    UsernameRemindRequestForm, UserRegistrationForm,
)
from core.views import (
    AccountSettingsView, LoginView, PasswordResetView,
    RegisterView, UsernameRemindDoneView, UsernameRemindView,
)

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
    alternative_urls = {
        'redirect_from_profile':
            PageWithFormTemplate._RequiresReverseURL(viewname='login', kwargs={
                'model_type': pgettext_lazy("URL", "profile"),
                'model_id': 0,
            }),
        'redirect_from_place':
            PageWithFormTemplate._RequiresReverseURL(viewname='login', kwargs={
                'model_type': pgettext_lazy("URL", "place"),
                'model_id': 0,
            }),
    }
    explicit_url = {
        'en': '/login/',
        'eo': '/ensaluti/',
    }
    template = 'registration/login.html'
    title = {
        'en': "Log in & Find accommodation | Pasporta Servo",
        'eo': "Ensalutu & Trovu loĝejon | Pasporta Servo",
    }
    alternative_titles = {
        'redirect_from_profile': {
            'en': "Log in & View profile details | Pasporta Servo",
            'eo': "Ensalutu & Rigardu detalojn de profilo | Pasporta Servo",
        },
        'redirect_from_place': {
            'en': "Log in & View place details | Pasporta Servo",
            'eo': "Ensalutu & Rigardu detalojn de loĝejo | Pasporta Servo",
        },
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


class PasswordResetRequestSuccessPage(PageTemplate):
    view_class = PasswordResetDoneView
    url = reverse_lazy('password_reset_done')
    explicit_url = {
        'en': '/password/reset/sent/',
        'eo': '/pasvorto/nova/sukceso/',
    }
    template = 'registration/password_reset_done.html'
    title = {
        'en': "Password reset at Pasporta Servo",
        'eo': "Nova pasvorto ĉe Pasporta Servo",
    }
    redirects_unauthenticated = False
    redirects_logged_in = False


class PasswordResetPage(PageWithFormTemplate):
    view_class = PasswordResetView
    form_class = SystemPasswordResetRequestForm
    url = reverse_lazy('password_reset')
    explicit_url = {
        'en': '/password/reset/',
        'eo': '/pasvorto/nova/',
    }
    template = 'registration/password_reset_form.html'
    title = {
        'en': "Password reset at Pasporta Servo",
        'eo': "Nova pasvorto ĉe Pasporta Servo",
    }
    redirects_unauthenticated = False
    redirects_logged_in = False
    form = {
        'selector': ".password.reset",
        'title': {
            'en': "Password reset",
            'eo': "Nova pasvorto",
        }
    }
    success_page = PasswordResetRequestSuccessPage


class UsernameRemindRequestSuccessPage(PageTemplate):
    view_class = UsernameRemindDoneView
    url = reverse_lazy('username_remind_done')
    explicit_url = {
        'en': '/username/remind/sent/',
        'eo': '/salutnomo/memorigo/sukceso/',
    }
    template = 'registration/username_remind_done.html'
    title = {
        'en': "Username at Pasporta Servo",
        'eo': "Salutnomo ĉe Pasporta Servo",
    }
    redirects_unauthenticated = False
    redirects_logged_in = False


class UsernameRemindPage(PageWithFormTemplate):
    view_class = UsernameRemindView
    form_class = UsernameRemindRequestForm
    url = reverse_lazy('username_remind')
    explicit_url = {
        'en': '/username/remind/',
        'eo': '/salutnomo/memorigo/',
    }
    template = 'registration/username_remind_form.html'
    title = {
        'en': "Username at Pasporta Servo",
        'eo': "Salutnomo ĉe Pasporta Servo",
    }
    redirects_unauthenticated = False
    redirects_logged_in = False
    form = {
        'selector': ".username.remind",
        'title': {
            'en': "Username reminder",
            'eo': "Memorigo pri salutnomo",
        }
    }
    success_page = UsernameRemindRequestSuccessPage


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
