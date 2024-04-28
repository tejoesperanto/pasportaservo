from django.urls import reverse_lazy

from pyquery import PyQuery

from core.forms import MassMailForm
from core.views import MassMailSentView, MassMailView

from .base import PageWithFormTemplate, PageWithTitleHeadingTemplate


class MassMailPage(PageWithFormTemplate):
    view_class = MassMailView
    form_class = MassMailForm
    url = reverse_lazy('mass_mail')
    explicit_url = {
        'en': '/admin/mass-mail/',
        'eo': '/admin/amassendado/',
    }
    template = 'core/mass_mail_form.html'
    title = {
        'en': "Announcement to users | Pasporta Servo",
        'eo': "Anonco al uzantoj | Pasporta Servo",
    }


class MassMailResultPage(PageWithTitleHeadingTemplate):
    view_class = MassMailSentView
    url = reverse_lazy('mass_mail_sent')
    explicit_url = {
        'en': '/admin/mass-mail/sent/',
        'eo': '/admin/amassendado/sukceso/',
    }
    template = 'core/mass_mail_sent.html'
    title = {
        'en': "Announcement to users | Pasporta Servo",
        'eo': "Anonco al uzantoj | Pasporta Servo",
    }
    page_title_success = {
        'en': "Emails sent",
        'eo': "Retmesaĝoj senditaj",
    }
    page_title_failure = {
        'en': "Emails not sent",
        'eo': "Retmesaĝoj ne senditaj",
    }

    def get_result_element(self) -> PyQuery:
        return self.pyquery("[role='main'] > h3")
