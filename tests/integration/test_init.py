from unittest import skipUnless
from unittest.mock import patch

from django.apps import apps
from django.conf import settings
from django.test import TestCase, tag

from gql.transport.exceptions import TransportError

from ..assertions import AdditionalAsserts


@tag('integration', 'init')
class AppLoadingTests(AdditionalAsserts, TestCase):
    def tearDown(self):
        apps.clear_cache()

    def test_no_feedback_url_prefetch(self):
        # When DISABLE_PREFETCH is True, the application is expected to avoid calls
        # to external services to get the corresponding URLs.
        with self.settings(GITHUB_DISABLE_PREFETCH=True):
            with patch('core.apps.GQLClient.execute') as mock_execute:
                with self.settings(INSTALLED_APPS=['core']):
                    self.assertIsNotNone(apps.get_app_config('core').models_module)
                    mock_execute.assert_not_called()
        del apps.all_models['core']

    def test_feedback_url_prefetching(self, comm_err=False):
        # When DISABLE_PREFETCH is False, the application is expected to call the
        # external services and get the corresponding URLs.
        # Note:: Since the loading operation (CoreConfig.ready) modifies a global
        # object, this test will change the feedback URLs for all other tests.
        dummy_url = "https://dum.my" if not comm_err else "http://alert.net"
        with self.settings(GITHUB_DISABLE_PREFETCH=False):
            with patch('core.apps.GQLClient.execute', return_value={'node': {'url': dummy_url}}) \
                    as mock_execute:
                if comm_err:
                    mock_execute.side_effect = TransportError
                with self.settings(INSTALLED_APPS=['core']):
                    self.assertIsNotNone(apps.get_app_config('core').models_module)
                    mock_execute.assert_called_once()
                    from core.models import FEEDBACK_TYPES
                    for feedback_type in FEEDBACK_TYPES.values():
                        with self.subTest(feedback=feedback_type):
                            if not comm_err:
                                self.assertEqual(feedback_type.url, dummy_url)
                            else:
                                self.assertNotEqual(feedback_type.url, dummy_url)
        del apps.all_models['core']

    def test_feedback_url_failed_prefetching(self):
        self.test_feedback_url_prefetching(comm_err=True)

    @tag('external')
    @skipUnless(settings.TEST_EXTERNAL_SERVICES, 'External services are tested only explicitly')
    def test_github_urls_integration_contract(self):
        # Note:: Since the loading operation (CoreConfig.ready) modifies a global
        # object, this test will change the feedback URLs for all other tests.
        with self.settings(GITHUB_DISABLE_PREFETCH=False):
            with self.settings(INSTALLED_APPS=['core']):
                from core.models import FEEDBACK_TYPES
                for feedback_type in FEEDBACK_TYPES.values():
                    with self.subTest(feedback=feedback_type):
                        self.assertStartsWith(feedback_type.url, settings.GITHUB_DISCUSSION_BASE_URL)
        del apps.all_models['core']
