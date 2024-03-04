from django.apps import AppConfig
from django.conf import settings
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from anymail.backends.base import AnymailBaseBackend
from anymail.message import AnymailMessage
from anymail.signals import pre_send


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
