from unittest.mock import PropertyMock, patch

from django.test import TestCase, override_settings, tag

from core.forms import FeedbackForm

from ..assertions import AdditionalAsserts


@tag('forms', 'feedback')
class FeedbackFormTests(AdditionalAsserts, TestCase):
    def test_init(self):
        form = FeedbackForm()
        expected_fields = {
            'feedback_on': True,
            'message': False,
            'private': False,
        }
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(expected_fields.keys()), set(form.fields))
        # Verify that fields are properly marked as required.
        for field in expected_fields:
            with self.subTest(field=field):
                self.assertIs(form.fields[field].required, expected_fields[field])
        # Verify that the `message` field will be auto-focused on load.
        self.assertIn('autofocus', form.fields['message'].widget.attrs)
        self.assertTrue(form.fields['message'].widget.attrs['autofocus'])

    @override_settings(GITHUB_DISCUSSION_BASE_URL='http://ps-ci.security/forum/')
    def test_help_text(self):
        form = FeedbackForm()
        with override_settings(LANGUAGE_CODE='en'):
            self.assertSurrounding(
                str(form.fields['message'].help_text),
                "Your contribution will appear in a discussion thread publicly visible on ",
                " without your name.")
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertSurrounding(
                str(form.fields['message'].help_text),
                "Via kontribuo aperos en diskuta fadeno publike konsultebla ĉe ",
                " sen via nomo.")

        with patch('core.models.FeedbackType.url', new_callable=PropertyMock) as mock_url:
            mock_url.return_value = 'http://disc.us/thread/17'
            form = FeedbackForm()
            self.assertIn(
                "<a href=\"http://disc.us/thread/17\" ",
                str(form.fields['message'].help_text))

            mock_url.return_value = ''
            form = FeedbackForm()
            self.assertIn(
                "<a href=\"http://ps-ci.security/forum/\" ",
                str(form.fields['message'].help_text))
