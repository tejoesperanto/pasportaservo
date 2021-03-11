from datetime import date

from django.test import tag

from django_webtest import WebTest

from ..factories import PolicyFactory


@tag('models')
class PolicyModelTests(WebTest):
    def test_effective_date(self):
        # The return value is expected to be a date object.
        policy = PolicyFactory()
        self.assertIsInstance(policy.effective_date, date)
        self.assertIsInstance(policy.__class__.get_effective_date_for_policy(policy.content), date)

        # A valid header is expected to result in a valid date object.
        policy = PolicyFactory(from_date="2019-06-01")
        self.assertEqual(policy.effective_date, date(2019, 6, 1))
        self.assertEqual(policy.__class__.get_effective_date_for_policy(policy.content), date(2019, 6, 1))

        # An empty header is expected to result in a warning and None.
        policy = PolicyFactory(from_date="")
        warning = "Policy does not indicate a date"
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.effective_date, None)
        self.assertIn(warning, str(cm.warning))
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.__class__.get_effective_date_for_policy(policy.content), None)
        self.assertIn(warning, str(cm.warning))
        # An invalid header is expected to result in a warning and None.
        policy = PolicyFactory(from_date="abcd")
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.effective_date, None)
        self.assertIn(warning, str(cm.warning))
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.__class__.get_effective_date_for_policy(policy.content), None)
        self.assertIn(warning, str(cm.warning))
        # An invalid header is expected to result in a warning and None.
        policy = PolicyFactory(from_date="YYYY-MM-DD")
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.effective_date, None)
        self.assertIn(warning, str(cm.warning))
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.__class__.get_effective_date_for_policy(policy.content), None)
        self.assertIn(warning, str(cm.warning))

        # A header with invalid date is expected to result in a warning and None.
        policy = PolicyFactory(from_date="1234-56-78")
        warning = "Policy effective date.* is invalid"
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.effective_date, None)
        self.assertRegex(str(cm.warning), warning)
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.__class__.get_effective_date_for_policy(policy.content), None)
        self.assertRegex(str(cm.warning), warning)
        # A header with invalid date is expected to result in a warning and None.
        policy = PolicyFactory(from_date="2019-02-29")
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.effective_date, None)
        self.assertRegex(str(cm.warning), warning)
        with self.assertWarns(UserWarning) as cm:
            self.assertIs(policy.__class__.get_effective_date_for_policy(policy.content), None)
        self.assertRegex(str(cm.warning), warning)
