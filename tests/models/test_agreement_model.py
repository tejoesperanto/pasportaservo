import re

from django.db import IntegrityError
from django.test import TestCase, override_settings, tag
from django.utils import timezone

from ..assertions import AdditionalAsserts
from ..factories import AgreementFactory, UserFactory


@tag('models')
class AgreementModelTests(AdditionalAsserts, TestCase):
    def test_field_max_lengths(self):
        accord = AgreementFactory.build()
        self.assertEqual(accord._meta.get_field('policy_version').max_length, 50)

    def test_field_blanks(self):
        accord = AgreementFactory.build()
        self.assertTrue(accord._meta.get_field('withdrawn').blank)
        self.assertFalse(accord._meta.get_field('policy_version').blank)

    def test_field_defaults(self):
        accord = AgreementFactory.build()
        self.assertIs(accord._meta.get_field('withdrawn').default, None)

    def test_str(self):
        expected_strings = {
            'en': 'User .+ agreed to \'{}\' ',
            'eo': 'Uzanto .+ akceptis \'{}\' ',
        }

        accord = AgreementFactory.create()
        policy_version_string = re.escape(accord.policy_version)
        for lang in expected_strings:
            with override_settings(LANGUAGE_CODE=lang):
                self.assertRegex(str(accord), expected_strings[lang].format(policy_version_string))

        accord = AgreementFactory.create(withdrawn=timezone.now())
        policy_version_string = re.escape(accord.policy_version)
        for lang in expected_strings:
            with override_settings(LANGUAGE_CODE=lang):
                self.assertRegex(str(accord), expected_strings[lang].format(policy_version_string))

    def test_duplicate_agreements_for_same_policy(self):
        policy_version = "terms_v1.2"
        user = UserFactory.create(agreement=None, profile=None)

        accord1 = AgreementFactory.create(user=user, policy_version=policy_version)
        with self.assertNotRaises(IntegrityError):
            accord2 = AgreementFactory.create(user=user, policy_version=policy_version)
        self.assertNotEqual(accord1.pk, accord2.pk)

        today = timezone.now()
        with self.assertNotRaises(IntegrityError):
            accord1.withdrawn = today
            accord1.save()
        with self.assertRaises(IntegrityError):
            accord2.withdrawn = today
            accord2.save()
