from django.urls import reverse_lazy

from pyquery import PyQuery

from core.forms import MassMailForm
from core.views import MassMailSentView, MassMailView

from .base import PageWithFormTemplate, PageWithTitleHeadingTemplate


class MassMailResultPage(PageWithTitleHeadingTemplate):
    view_class = MassMailSentView
    url = reverse_lazy('mass_mail_sent')
    alternative_urls = {
        'via_async_task':
            PageWithFormTemplate._RequiresReverseURL(viewname='mass_mail_sent', kwargs={
                'task_id': '00001112223334445556667778889999',
            }),
    }
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
        'base': {
            'en': "Emails sent",
            'eo': "Retmesaĝoj senditaj",
        },
        'via_async_task': {
            'en': "Emails enqueued",
            'eo': "Retmesaĝoj envicigitaj",
        },
    }
    page_title_failure = {
        'base': {
            'en': "Emails not sent",
            'eo': "Retmesaĝoj ne senditaj",
        },
        'via_async_task': {
            'en': "Emails not enqueued",
            'eo': "Retmesaĝoj ne envicigitaj",
        },
    }

    def get_result_element(self) -> PyQuery:
        return self.pyquery("[role='main'] > h3")


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
    success_page = MassMailResultPage
