from django.apps import AppConfig
from django.conf import settings
from django.core.mail import mail_admins
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, ngettext

from anymail.backends.base import AnymailBaseBackend
from anymail.message import AnymailMessage
from anymail.signals import pre_send

from core.templatetags.domain import domain


class ChatConfig(AppConfig):
    name = "chat"
    verbose_name = _("Communicator")


@receiver(pre_send)
def enrich_envelope(sender: type[AnymailBaseBackend], message: AnymailMessage, **kwargs):
    if getattr(message, 'mass_mail', False):
        # Mass emails must be sent via the broadcast stream.
        return
    if message.subject.startswith('[[CHAT]]'):
        extra = getattr(message, 'esp_extra', {})
        extra['MessageStream'] = 'notifications-to-users'
        message.esp_extra = extra
        message.tags = ['notification:chat']
        message.track_opens = True
        message.metadata = {'env': settings.ENVIRONMENT}
        message.subject = message.subject.removeprefix('[[CHAT]]').strip()


def notify_pending_messages():
    from postman.models import PendingMessage

    pending_count = PendingMessage.objects.count()
    if pending_count == 0:
        return
    mail_admins(
        ngettext(
            # xgettext:python-brace-format
            "Note to admin: There is currently {} chat message pending moderation.",
            "Note to admin: There are currently {} chat messages pending moderation.",
            pending_count
        ).format(pending_count),
        domain({}, reverse('admin:postman_pendingmessage_changelist')),
    )
