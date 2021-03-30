from collections import namedtuple
from datetime import timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.utils.timezone import make_aware

from faker import Faker

from hosting.managers import (
    NotDeletedManager, NotDeletedRawManager, TrackingManager,
)


class TrackingManagersTests:
    def test_manager_classes(self):
        model = self.factory._meta.model

        self.assertTrue(hasattr(model, 'objects'))
        self.assertIsInstance(model.objects, NotDeletedManager)

        self.assertTrue(hasattr(model, 'objects_raw'))
        self.assertIsInstance(model.objects_raw, NotDeletedRawManager)

        self.assertTrue(hasattr(model, 'all_objects'))
        self.assertIsInstance(model.all_objects, TrackingManager)

    @patch('hosting.managers.SiteConfiguration.get_solo',
           return_value=namedtuple('DummyConfig', 'confirmation_validity_period')(timedelta(days=35)))
    def test_manager_flags(self, mock_config):
        model = self.factory._meta.model
        faker = Faker()
        existing_items_count = {
            manager_name: getattr(model, manager_name).count()
            for manager_name in ['objects', 'objects_raw', 'all_objects']
        }
        from_period = lambda start, end: make_aware(faker.date_time_between(start, end))
        test_data = [
            self.factory(),
            self.factory(confirmed_on=from_period('-30d', '-20d')),
            self.factory(confirmed_on=from_period('-60d', '-40d'), deleted_on=from_period('-10d', '-2d')),
            self.factory(checked_on=from_period('-30d', '-20d')),
            self.factory(checked_on=from_period('-60d', '-40d'), deleted_on=from_period('-10d', '-2d')),
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
        qs = model.all_objects.order_by('-id')
        with self.subTest(manager='all_objects'):
            self.assertEqual(len(qs), 5 + existing_items_count['all_objects'])
            for obj in qs:
                self.assertTrue(hasattr(obj, 'deleted'))
                self.assertIs(obj.deleted, True if obj.deleted_on else False)
                self.assertTrue(hasattr(obj, 'confirmed'))
                self.assertTrue(hasattr(obj, 'checked'))

        # Object which was confirmed within the confirmation validity period
        # is expected to have the 'confirmed' flag set to True.
        self.assertEqual(qs[3].pk, test_data[1].pk)
        self.assertTrue(qs[3].confirmed)
        # Object which was confirmed outside the confirmation validity period
        # is expected to have the 'confirmed' flag set to False.
        self.assertEqual(qs[2].pk, test_data[2].pk)
        self.assertFalse(qs[2].confirmed)
        # Object which was checked within the confirmation validity period
        # is expected to have the 'checked' flag set to True.
        self.assertEqual(qs[1].pk, test_data[3].pk)
        self.assertTrue(qs[1].checked)
        # Object which was checked outside the confirmation validity period
        # is expected to have the 'checked' flag set to True.
        # (Check exvalidation is turned off at the moment.)
        self.assertEqual(qs[0].pk, test_data[4].pk)
        self.assertTrue(qs[0].checked)

    @patch('hosting.managers.SiteConfiguration.get_solo', side_effect=DatabaseError)
    def test_manager_defaults(self, mock_config):
        model = self.factory._meta.model
        faker = Faker()
        # The default validity period is expected to be 42 weeks.
        self.factory(confirmed_on=make_aware(faker.date_time_between('-288d', '-293d')))
        self.factory(confirmed_on=make_aware(faker.date_time_between('-295d', '-300d')))
        qs = model.all_objects.order_by('-id')
        self.assertFalse(qs[0].confirmed)
        self.assertTrue(qs[1].confirmed)
