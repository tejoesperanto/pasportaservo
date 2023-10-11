from django.urls import reverse_lazy

from core.forms import UserRegistrationForm
from core.views import RegisterView

from .base import PageWithFormTemplate


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
