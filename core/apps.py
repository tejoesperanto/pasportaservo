from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

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
