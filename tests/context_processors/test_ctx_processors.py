from django.conf import settings

from django_webtest import WebTest


class CoreContextProcessorTests(WebTest):
    def test_settings_exposure(self):
        response = self.app.get('/', status=200)
        for setting in ('MAPBOX_GL_CSS',
                        'MAPBOX_GL_JS',
                        'INVALID_PREFIX',
                        'REDIRECT_FIELD_NAME',
                        'ENVIRONMENT'):
            with self.subTest(setting=setting):
                self.assertTrue(setting in response.context, msg="'{}' not present in the context".format(setting))
                self.assertEqual(response.context[setting], getattr(settings, setting))
