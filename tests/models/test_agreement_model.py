import re
from typing import cast

from django.test import TestCase, override_settings, tag
from django.utils import timezone

from core.models import Agreement

from ..factories import AgreementFactory


@tag('models')
class AgreementModelTests(TestCase):
    def test_field_max_lengths(self):
        accord = cast(Agreement, AgreementFactory.build())
        self.assertEqual(accord._meta.get_field('policy_version').max_length, 50)

    def test_field_blanks(self):
        accord = cast(Agreement, AgreementFactory.build())
        self.assertTrue(accord._meta.get_field('withdrawn').blank)
        self.assertFalse(accord._meta.get_field('policy_version').blank)

    def test_field_defaults(self):
        accord = cast(Agreement, AgreementFactory.build())
        self.assertIs(accord._meta.get_field('withdrawn').default, None)

    def test_str(self):
        expected_strings = {
            'en': 'User .+ agreed to \'{}\' ',
            'eo': 'Uzanto .+ akceptis \'{}\' ',
        }

        accord = cast(Agreement, AgreementFactory())
        policy_version_string = re.escape(accord.policy_version)
        for lang in expected_strings:
            with override_settings(LANGUAGE_CODE=lang):
                self.assertRegex(str(accord), expected_strings[lang].format(policy_version_string))

        accord = cast(Agreement, AgreementFactory(withdrawn=timezone.now()))
        policy_version_string = re.escape(accord.policy_version)
        for lang in expected_strings:
            with override_settings(LANGUAGE_CODE=lang):
                self.assertRegex(str(accord), expected_strings[lang].format(policy_version_string))
