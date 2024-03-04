import re

from django.apps import AppConfig
from django.conf import settings
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from anymail.backends.base import AnymailBaseBackend
from anymail.message import AnymailMessage
from anymail.signals import pre_send
from gql import Client as GQLClient, gql
from gql.transport.exceptions import TransportError, TransportQueryError
from gql.transport.requests import RequestsHTTPTransport as GQLHttpTransport


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = _("Hosting Service Core")

    def ready(self):
        if getattr(settings, 'GITHUB_DISABLE_PREFETCH', False):
            return

        # Iterate over the user feedback endpoints enabled and fetch their
        # current URLs from the remote forum (GitHub at present).
        from .models import FEEDBACK_TYPES
        transport = GQLHttpTransport(
            settings.GITHUB_GRAPHQL_HOST, auth=settings.GITHUB_ACCESS_TOKEN)
        client = GQLClient(transport=transport, fetch_schema_from_transport=True)
        query = gql("""
            query($disc_id: ID!) {
                node (id: $disc_id) { ... on Discussion {
                    url
                } }
            }
        """)
        for feedback_key, feedback in FEEDBACK_TYPES.items():
            try:
                discussion = client.execute(
                    query,
                    variable_values={'disc_id': feedback.foreign_id})
            except (TransportError, TransportQueryError):
                pass
            else:
                FEEDBACK_TYPES[feedback_key] = (
                    feedback._replace(url=discussion['node']['url'])
                )


@receiver(pre_send)
def enrich_envelope(sender: type[AnymailBaseBackend], message: AnymailMessage, **kwargs):
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
    possible_prefixes_pattern = '|'.join(re.escape(prefix) for prefix in tags.keys())
    if match := re.match(possible_prefixes_pattern, message.subject):
        extra = getattr(message, 'esp_extra', {})
        extra['MessageStream'] = 'notifications-to-users'
        message.esp_extra = extra
        message.tags = [f'notification:{tags[match.group()]}']
        message.metadata = {'env': settings.ENVIRONMENT}
        message.subject = message.subject.removeprefix(match.group()).strip()
