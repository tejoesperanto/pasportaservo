import re

from django.test import override_settings, tag
from django.utils import timezone

from django_webtest import WebTest

from ..factories import AgreementFactory


@tag('models')
class AgreementModelTests(WebTest):
    def test_field_max_lengths(self):
        accord = AgreementFactory.build()
        self.assertEqual(accord._meta.get_field('policy_version').max_length, 50)

    def test_field_blanks(self):
        accord = AgreementFactory.build()
        self.assertTrue(accord._meta.get_field('withdrawn').blank)

    def test_field_defaults(self):
        accord = AgreementFactory.build()
        self.assertIs(accord._meta.get_field('withdrawn').default, None)

    def test_str(self):
        expected_strings = {
            'en': 'User .+ agreed to \'{}\' ',
            'eo': 'Uzanto .+ akceptis \'{}\' ',
        }

        accord = AgreementFactory()
        policy_version_string = re.escape(accord.policy_version)
        for lang in expected_strings:
            with override_settings(LANGUAGE_CODE=lang):
                self.assertRegex(str(accord), expected_strings[lang].format(policy_version_string))

        accord = AgreementFactory(withdrawn=timezone.now())
        policy_version_string = re.escape(accord.policy_version)
        for lang in expected_strings:
            with override_settings(LANGUAGE_CODE=lang):
                self.assertRegex(str(accord), expected_strings[lang].format(policy_version_string))
