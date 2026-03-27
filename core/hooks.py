import logging
import re

from django.conf import settings
from django.dispatch import receiver

import anymail.signals as mail_signals
from anymail.backends.base import AnymailBaseBackend
from anymail.message import AnymailMessage
from anymail.signals import AnymailTrackingEvent, EventType as AnymailEventType
from anymail.webhooks.base import AnymailBaseWebhookView

from hosting.models import Profile

webhook_log = logging.getLogger('PasportaServo.webhook')


@receiver(mail_signals.pre_send, dispatch_uid='Duplicate signal registration prevention')
def enrich_envelope(
        sender: type[AnymailBaseBackend],
        message: AnymailMessage,
        **kwargs,
):
    """
    Add extra Anymail / Postmark information to an email message, for correct
    processing. This is done via a `pre_send` signal because Django sends
    emails in multiple manners, and customizing each one of them individually
    is quite cumbersome.
    `message` can be an EmailMessage, an EmailMultiAlternatives, or a derivative.
    """
    if getattr(message, 'mass_mail', False):
        # Mass emails must be sent via the broadcast stream.
        return
    tags = {
        '[[ACCOUNT]]': 'account',
        '[[ACCOUNT-EMAIL]]': 'email',
        '[[PLACE-DETAILS]]': 'authorized',
    }
    possible_prefixes_re = '|'.join(re.escape(prefix) for prefix in tags.keys())
    if match := re.match(possible_prefixes_re, message.subject):
        extra = getattr(message, 'esp_extra', {})
        extra['MessageStream'] = 'notifications-to-users'
        message.esp_extra = extra
        message.tags = [f'notification:{tags[match.group()]}']
        message.metadata = {'env': settings.ENVIRONMENT}
        message.subject = message.subject.removeprefix(match.group()).strip()


@receiver(mail_signals.tracking, dispatch_uid='Duplicate signal registration prevention')
def process_suppression(
        sender: type[AnymailBaseWebhookView],
        event: AnymailTrackingEvent,
        esp_name: str,
        **kwargs,
):
    suppresion_events = [
        AnymailEventType.REJECTED,
        AnymailEventType.BOUNCED,
        AnymailEventType.COMPLAINED,
    ]
    obfuscated_recipient = (
        event.recipient if settings.DEBUG
        else f"{event.recipient.partition('@')[0]}@..."
    )
    webhook_log.info(
        f"Event received '{event.event_type}' for email address <{obfuscated_recipient}>"
    )
    if event.event_type not in suppresion_events:
        return
    if 'env' in event.metadata and event.metadata['env'] != settings.ENVIRONMENT:
        return
    Profile.mark_invalid_emails([event.recipient])
