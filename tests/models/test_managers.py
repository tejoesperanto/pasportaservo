from collections import namedtuple
from datetime import timedelta
from typing import TYPE_CHECKING, ClassVar
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.utils.timezone import make_aware

from factory import Faker
from factory.django import DjangoModelFactory
from waffle.testutils import override_switch

from hosting.managers import (
    NotDeletedManager, NotDeletedRawManager, TrackingManager,
)
from hosting.models import TrackingModel


class TrackingManagersTests(TestCase if TYPE_CHECKING else object):
    factory: ClassVar[type[DjangoModelFactory]]

    def test_manager_classes(self):
        model: TrackingModel = self.factory._meta.model

        self.assertTrue(hasattr(model, 'objects'))
        self.assertIsInstance(model.objects, NotDeletedManager)

        self.assertTrue(hasattr(model, 'objects_raw'))
        self.assertIsInstance(model.objects_raw, NotDeletedRawManager)

        self.assertTrue(hasattr(model, 'all_objects'))
        self.assertIsInstance(model.all_objects, TrackingManager)

    @patch('hosting.managers.SiteConfiguration.get_solo')
    def test_manager_flags(self, mock_config):
        model: TrackingModel = self.factory._meta.model
        mock_config.return_value = (
            namedtuple('DummyConfig', 'confirmation_validity_period')(timedelta(days=35))
        )
        faker = Faker._get_faker()
        existing_items_count = {
            manager_name: getattr(model, manager_name).count()
            for manager_name in ['objects', 'objects_raw', 'all_objects']
        }

        def from_period(start: str, end: str):
            return make_aware(faker.date_time_between(start, end))
        test_data = [
            self.factory(),
            self.factory(confirmed_on=from_period('-30d', '-20d')),
            self.factory(confirmed_on=from_period('-60d', '-40d'),
                         deleted_on=from_period('-10d', '-2d')),
            self.factory(checked_on=from_period('-30d', '-20d')),
            self.factory(checked_on=from_period('-60d', '-40d'),
                         deleted_on=from_period('-10d', '-2d')),
        ]

        # The `objects` manager is expected to fetch only non-deleted,
        # annotated, instances of the model.
        qs = model.objects.order_by('id')
        with self.subTest(manager='objects'):
            self.assertEqual(len(qs), 3 + existing_items_count['objects'])
            for obj in qs:
                self.assertTrue(hasattr(obj, 'deleted'))
                self.assertFalse(obj.deleted, msg=f"object deleted on = {obj.deleted_on}")
                self.assertTrue(hasattr(obj, 'confirmed'))
                self.assertTrue(hasattr(obj, 'checked'))

        # The `objects_raw` manager is expected to fetch only non-deleted,
        # non-annotated, instances of the model.
        qs = model.objects_raw.order_by('id')
        with self.subTest(manager='objects_raw'):
            self.assertEqual(len(qs), 3 + existing_items_count['objects_raw'])
            for obj in qs:
                self.assertFalse(hasattr(obj, 'deleted'))
                self.assertIsNone(obj.deleted_on)
                self.assertFalse(hasattr(obj, 'confirmed'))
                self.assertFalse(hasattr(obj, 'checked'))

        # The `all_objects` manager is expected to fetch all instances of
        # the model, with boolean flag annotations.
        qs = model.all_objects.order_by('id')
        with self.subTest(manager='all_objects'):
            self.assertEqual(len(qs), 5 + existing_items_count['all_objects'])
            for obj in qs:
                self.assertTrue(hasattr(obj, 'deleted'))
                self.assertIs(obj.deleted, True if obj.deleted_on else False)
                self.assertTrue(hasattr(obj, 'confirmed'))
                self.assertTrue(hasattr(obj, 'checked'))

        # For no expiry of the confirmations, any date is expected to result
        # in the object being marked as confirmed. Otherwise, only the more
        # recent date is expected to do so.
        for confirm_expiry in (True, False):
            with (
                override_switch('HOSTING_DATA_CONFIRMATION_EXPIRY', confirm_expiry),
                self.subTest(expires=confirm_expiry)
            ):
                qs = model.all_objects.order_by('-id')
                self.assertEqual(qs[4].pk, test_data[0].pk)
                self.assertFalse(qs[4].confirmed)
                # Object which was confirmed within the confirmation validity
                # period is expected to have the 'confirmed' flag set to True.
                self.assertEqual(qs[3].pk, test_data[1].pk)
                self.assertTrue(qs[3].confirmed)
                # Object which was confirmed outside the confirmation validity
                # period is expected to have the 'confirmed' flag set to True
                # if confirmations do not expire, otherwise to False.
                self.assertEqual(qs[2].pk, test_data[2].pk)
                self.assertIs(qs[2].confirmed, False if confirm_expiry else True)

        # For no expiry of the verifications, any date is expected to result
        # in the object being marked as checked. Otherwise, only the more
        # recent date is expected to do so.
        for verify_expiry in (True, False):
            with (
                override_switch('HOSTING_DATA_VERIFICATION_EXPIRY', verify_expiry),
                self.subTest(expires=verify_expiry)
            ):
                qs = model.all_objects.order_by('-id')
                self.assertEqual(qs[4].pk, test_data[0].pk)
                self.assertFalse(qs[4].checked)
                # Object which was checked within the confirmation validity
                # period is expected to have the 'checked' flag set to True.
                self.assertEqual(qs[1].pk, test_data[3].pk)
                self.assertTrue(qs[1].checked)
                # Object which was checked outside the confirmation validity
                # period is expected to have the 'checked' flag set to True
                # if verifications do not expire, otherwise to False.
                self.assertEqual(qs[0].pk, test_data[4].pk)
                self.assertIs(qs[0].checked, False if verify_expiry else True)

    @patch('hosting.managers.get_waffle_switch_model')
    @patch('hosting.managers.SiteConfiguration')
    def test_manager_defaults(self, mock_config, mock_switch):
        model: TrackingModel = self.factory._meta.model
        faker = Faker._get_faker()
        mock_config.get_solo.side_effect = DatabaseError
        mock_switch.return_value.get.side_effect = DatabaseError
        # The default validity period is expected to be 42 weeks, with user
        # confirmations expiring by default and supervisor verifications
        # not expiring.
        self.factory(
            confirmed_on=make_aware(faker.date_time_between('-288d', '-293d')),
            checked_on=make_aware(faker.date_time_between('-288d', '-293d')),
        )
        self.factory(
            confirmed_on=make_aware(faker.date_time_between('-295d', '-300d')),
            checked_on=make_aware(faker.date_time_between('-730d', '-735d')),
        )
        qs = model.all_objects.order_by('-id')
        self.assertFalse(qs[0].confirmed)
        self.assertTrue(qs[0].checked)
        self.assertTrue(qs[1].confirmed)
        self.assertTrue(qs[1].checked)
