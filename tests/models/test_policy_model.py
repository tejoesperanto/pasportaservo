from datetime import date
from typing import cast

from django.conf import settings
from django.test import TestCase, override_settings, tag

from factory import Faker

from core.managers import PoliciesManager
from core.models import Policy

from ..assertions import AdditionalAsserts
from ..factories import PolicyFactory


@tag('models')
class PolicyModelTests(TestCase):
    def test_field_max_lengths(self):
        policy = cast(Policy, PolicyFactory.build())
        self.assertEqual(policy._meta.get_field('version').max_length, 50)
        self.assertIsNone(policy._meta.get_field('content').max_length)
        self.assertIsNone(policy._meta.get_field('changes_summary').max_length)

    def test_field_blanks(self):
        policy = cast(Policy, PolicyFactory.build())
        self.assertTrue(policy._meta.get_field('changes_summary').blank)
        self.assertFalse(policy._meta.get_field('version').blank)
        self.assertFalse(policy._meta.get_field('effective_date').blank)
        self.assertFalse(policy._meta.get_field('content').blank)

    def test_field_defaults(self):
        policy = cast(Policy, PolicyFactory.build())
        self.assertIs(policy._meta.get_field('requires_consent').default, True)

    def test_field_uniqueness(self):
        policy = cast(Policy, PolicyFactory.build())
        self.assertTrue(policy._meta.get_field('version').unique)
        self.assertTrue(policy._meta.get_field('effective_date').unique)

    def test_str(self):
        expected_strings = {
            'en': {
                True: 'Policy {p.version} binding from {p.effective_date:%Y-%m-%d}',
                False: 'Policy {p.version} effective from {p.effective_date:%Y-%m-%d}',
            },
            'eo': {
                True: 'Regularo {p.version} deviga ekde {p.effective_date:%Y-%m-%d}',
                False: 'Regularo {p.version} en efiko ekde {p.effective_date:%Y-%m-%d}',
            },
        }

        for consent in True, False:
            policy = cast(Policy, PolicyFactory(requires_consent=consent))
            for lang in expected_strings:
                with override_settings(LANGUAGE_CODE=lang):
                    with self.subTest(consent=consent, LANGUAGE_CODE=lang):
                        self.assertEqual(
                            str(policy),
                            expected_strings[lang][consent].format(p=policy)
                        )


@tag('models')
class PoliciesManagerTests(AdditionalAsserts, TestCase):
    @classmethod
    def setUpTestData(cls):
        Policy.objects.all().delete()
        policies = PolicyFactory.create_batch(3, from_past_date=True)
        cls.effective_policies = [
            sorted(cast(list[Policy], policies), key=lambda p: p.effective_date)[-1],
        ]
        policies = PolicyFactory.create_batch(
            2,
            effective_date=Faker('date_between', start_date='-360d', end_date='-2d'),
            requires_consent=False)
        cls.effective_policies.extend(
            sorted(cast(list[Policy], policies), key=lambda p: p.effective_date)
        )
        PolicyFactory.create_batch(2, from_future_date=True)
        PolicyFactory.create_batch(
            1,
            effective_date=Faker('date_between', start_date='+2d', end_date='+360d'),
            requires_consent=False)
        policies = [PolicyFactory.create(
            effective_date=date.today(),
            requires_consent=False)]
        cls.effective_policies.append(policies[0])

    def test_manager_class(self):
        mgr = Policy.objects
        self.assertIsInstance(mgr, PoliciesManager)

    def test_get_latest(self):
        self.assertEqual(
            Policy.objects.latest(),
            Policy.objects.order_by('-effective_date').first()
        )

    def test_get_latest_effective(self):
        policy = Policy.objects.latest_efective()
        self.assertEqual(policy.version, self.effective_policies[-1].version)
        self.assertEqual(policy.effective_date, self.effective_policies[-1].effective_date)

        policy = Policy.objects.latest_efective(requiring_consent=True)
        self.assertEqual(policy.version, self.effective_policies[0].version)
        self.assertEqual(policy.effective_date, self.effective_policies[0].effective_date)

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_get_all_effective(self):
        versions, policies = Policy.objects.all_effective()
        expected_count = 4
        self.assertLength(versions, expected_count)
        self.assertLength(policies, expected_count)
        for i, policy in enumerate(policies):
            policy = cast(Policy, policy)
            with self.subTest(policy_nr=i, policy_ver=policy.version):
                self.assertEqual(
                    policy.version,
                    self.effective_policies[expected_count-i-1].version)
                self.assertEqual(
                    policy.effective_date,
                    self.effective_policies[expected_count-i-1].effective_date)
        self.assertEqual(set(versions), set(p.version for p in self.effective_policies))

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_get_all_effective_today(self):
        Policy.objects.filter(effective_date=date.today()).update(requires_consent=True)
        versions, policies = Policy.objects.all_effective()
        self.assertLength(versions, 1)
        self.assertLength(policies, 1)
        self.assertEqual(policies[0].version, self.effective_policies[-1].version)
        self.assertEqual(
            policies[0].effective_date,
            self.effective_policies[-1].effective_date)
