from django.conf import settings

from django_webtest import WebTest


class CoreContextProcessorTests(WebTest):
    def test_settings_exposure(self):
        response = self.app.get('/', status=200)
        for setting in ('CURRENT_COMMIT',
                        'INVALID_PREFIX',
                        'SEARCH_FIELD_NAME',
                        'SUPPORT_EMAIL',
                        'REDIRECT_FIELD_NAME',
                        'ENVIRONMENT'):
            with self.subTest(setting=setting):
                self.assertTrue(setting in response.context, msg="'{}' not present in the context".format(setting))
                self.assertEqual(response.context[setting], getattr(settings, setting))
        setting = 'HOUR'
        with self.subTest(setting=setting):
            self.assertTrue(setting in response.context, msg="'{}' not present in the context".format(setting))
            self.assertEqual(response.context[setting], 3600)
