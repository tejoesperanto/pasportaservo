import re

from django.test import override_settings, tag
from django.utils import timezone
from django_webtest import WebTest

from ..factories import AgreementFactory


@tag("models")
class AgreementModelTests(WebTest):
    def test_field_max_lengths(self):
        accord = AgreementFactory.build()
        self.assertEqual(accord._meta.get_field("policy_version").max_length, 50)

    def test_field_blanks(self):
        accord = AgreementFactory.build()
        self.assertTrue(accord._meta.get_field("withdrawn").blank)

    def test_field_defaults(self):
        accord = AgreementFactory.build()
        self.assertIs(accord._meta.get_field("withdrawn").default, None)

    @override_settings(LANGUAGE_CODE="en")
    def test_str(self):
        accord = AgreementFactory()
        self.assertRegex(
            str(accord),
            "User .+ agreed to '{}' ".format(re.escape(accord.policy_version)),
        )
        accord = AgreementFactory(withdrawn=timezone.now())
        self.assertRegex(
            str(accord),
            "User .+ agreed to '{}' ".format(re.escape(accord.policy_version)),
        )
