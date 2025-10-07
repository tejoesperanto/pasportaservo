from datetime import date
from typing import cast
from unittest.mock import PropertyMock, patch

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase, override_settings, tag
from django.utils import timezone

from django_countries.fields import Country
from factory import Faker

from hosting.fields import RangeIntegerField
from hosting.managers import AvailableManager

from ..assertions import AdditionalAsserts
from ..factories import PlaceFactory
from .test_managers import TrackingManagersTests


@tag('models', 'place')
class PlaceModelTests(AdditionalAsserts, TrackingManagersTests, TestCase):
    factory = PlaceFactory

    @classmethod
    def setUpTestData(cls):
        cls.basic_place = PlaceFactory.create()

    def test_field_max_lengths(self):
        place = self.basic_place
        self.assertEqual(place._meta.get_field('city').max_length, 255)
        self.assertEqual(place._meta.get_field('closest_city').max_length, 255)
        self.assertEqual(place._meta.get_field('postcode').max_length, 11)
        self.assertEqual(place._meta.get_field('state_province').max_length, 70)
        self.assertEqual(place._meta.get_field('short_description').max_length, 140)

    def test_field_limits(self):
        place = self.basic_place
        # Verify the expected limits of the maximum number of guests.
        max_guest_field = cast(RangeIntegerField, place._meta.get_field('max_guest'))
        self.assertEqual(max_guest_field.min_value, 1)
        self.assertEqual(max_guest_field.max_value, 50)
        # Verify the expected limits of the maximum number of nights.
        max_night_field = cast(RangeIntegerField, place._meta.get_field('max_night'))
        self.assertEqual(max_night_field.min_value, 1)
        self.assertEqual(max_night_field.max_value, 180)
        # Verify that the number of days prior contact is 0 or higher.
        place.contact_before = -1
        with self.assertRaises(ValidationError) as cm:
            place.clean_fields()
        self.assertIn('contact_before', cm.exception.message_dict)
        place.contact_before = 0
        self.assertNotRaises(ValidationError, lambda: place.clean_fields())

    def test_available_manager(self):
        model = self.basic_place._meta.model
        # The Place model is expected to have the 'available_objects' manager.
        self.assertTrue(hasattr(model, 'available_objects'))
        self.assertIsInstance(model.available_objects, AvailableManager)
        # The manager is expected to fetch only places which are marked available.
        PlaceFactory(owner=self.basic_place.owner, available=False)
        qs = model.available_objects.order_by('id')
        self.assertTrue(self.basic_place.available)
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].pk, self.basic_place.pk)

    def test_icon(self):
        place = self.basic_place
        self.assertSurrounding(place.icon, "<span ", "></span>")
        self.assertIn(" title=", place.icon)

    def test_owner_available(self):
        place = self.basic_place
        # A place's owner who does not meet and does not guide is expected
        # to be marked as unavailable.
        place.tour_guide = False
        place.have_a_drink = False
        self.assertFalse(place.owner_available)
        # A place's owner who meets but does not guide is expected to be marked
        # as available.
        place.tour_guide = False
        place.have_a_drink = True
        self.assertTrue(place.owner_available)
        # A place's owner who does not meet but guides is expected to be marked
        # as available.
        place.tour_guide = True
        place.have_a_drink = False
        self.assertTrue(place.owner_available)
        # A place's owner who both meets and guides is expected to be marked
        # as available.
        place.tour_guide = True
        place.have_a_drink = True
        self.assertTrue(place.owner_available)

    def test_is_blocked(self):
        place = self.basic_place
        faker = Faker._get_faker()

        # A place without blocking dates is expected to be unblocked.
        place.blocked_from = None
        place.blocked_until = None
        self.assertFalse(place.is_blocked)

        # A place with blocking start date and without unblocking date
        # is expected to be blocked.
        place.blocked_from = faker.past_date()
        self.assertTrue(place.is_blocked)
        place.blocked_from = date.today()
        self.assertTrue(place.is_blocked)
        place.blocked_from = faker.future_date()
        self.assertTrue(place.is_blocked)

        # A place without blocking start date and with unblocking date in the past
        # is expected to be unblocked.
        place.blocked_from = None
        place.blocked_until = faker.past_date()
        self.assertFalse(place.is_blocked)
        # A place without blocking start date and with future unblocking date
        # is expected to be blocked.
        place.blocked_until = date.today()
        self.assertTrue(place.is_blocked)
        place.blocked_until = faker.future_date()
        self.assertTrue(place.is_blocked)

        # A place with blocking dates in the past is expected to be unblocked.
        place.blocked_from = faker.date_between(start_date='-2y', end_date='-1y')
        place.blocked_until = faker.date_between(start_date='-11M', end_date='-1d')
        self.assertFalse(place.is_blocked)
        # A place with blocking start date in the past and with future unblocking date
        # is expected to be blocked.
        place.blocked_from = faker.date_between(start_date='-2y', end_date='-1y')
        place.blocked_until = date.today()
        self.assertTrue(place.is_blocked)
        place.blocked_from = faker.date_between(start_date='-2y', end_date='-1y')
        place.blocked_until = faker.future_date()
        self.assertTrue(place.is_blocked)

        # A place with future blocking start date is expected to be blocked.
        place.blocked_from = date.today()
        place.blocked_until = date.today()
        self.assertTrue(place.is_blocked)
        place.blocked_from = date.today()
        place.blocked_until = faker.future_date()
        self.assertTrue(place.is_blocked)
        place.blocked_from = faker.date_between(start_date='+1d', end_date='+11M')
        place.blocked_until = faker.date_between(start_date='+1y', end_date='+2y')
        self.assertTrue(place.is_blocked)

    def test_locality_display(self):
        place = self.basic_place

        # A place in a known city is expected to be "City-name (Country-name)".
        place.city = "Córdoba"
        place.country = Country('ES')
        for lang, country_name in {'en': "Spain", 'eo': "Hispanio"}.items():
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                self.assertEqual(place.get_locality_display(), f'Córdoba ({country_name})')

        # A place in an unknown city is expected to be "Country-name".
        place.city = ""
        place.country = Country('PT')
        for lang, country_name in {'en': "Portugal", 'eo': "Portugalio"}.items():
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                self.assertEqual(place.get_locality_display(), country_name)

        # A place in a known city is expected to be "City-name (Country-name)".
        place.city = Faker._get_faker('nl').city()
        place.country = Country('NL')
        self.assertEqual(
            place.get_locality_display(),
            '{} ({})'.format(place.city, place.country.name)
        )

    def test_postcode_display(self):
        place = self.basic_place

        # For a place with no postcode, the result is expected to be an empty string.
        place.postcode = ""
        place.country = Country('AZ')
        self.assertEqual(place.get_postcode_display(), "")
        place.postcode = ""
        place.country = Country('KY')
        self.assertEqual(place.get_postcode_display(), "")

        # For a place with postcode in country with no postcode prefix,
        # the result is expected to be the indicated postcode.
        place.postcode = "AB 8734/X"
        place.country = Country('CK')
        self.assertEqual(place.get_postcode_display(), "AB 8734/X")

        # For a place with postcode in country with optional postcode prefix,
        # the result is expected to start with the prefix.
        place.postcode = "56129"
        place.country = Country('LT')
        self.assertEqual(place.get_postcode_display(), "LT-56129")
        place.postcode = "LT-45238"
        self.assertEqual(place.get_postcode_display(), "LT-45238")

        # For a place with postcode in country with mandatory postcode prefix,
        # the result is expected to include the prefix only once.
        place.postcode = "LV-8520"
        place.country = Country('LV')
        self.assertEqual(place.get_postcode_display(), "LV-8520")

        # The result is expected to be calculated only once and memoized
        # until the postcode is modified.
        place = PlaceFactory.build(
            owner=self.basic_place.owner, postcode=True, country=Country('HT'))
        with (
            patch('hosting.models.Place.postcode', new_callable=PropertyMock)
            as mock_postcode
        ):
            place.get_postcode_display()
            place.get_postcode_display()
            # Postcode is accessed thrice during calculation.
            self.assertEqual(mock_postcode.call_count, 3)

            place.postcode = PlaceFactory.generate_postcode(place.country)
            mock_postcode.reset_mock()
            place.get_postcode_display()
            # Postcode is accessed thrice during calculation.
            self.assertEqual(mock_postcode.call_count, 3)

    def test_str(self):
        place = self.basic_place

        # A place in a known city is expected to be "City-name, Country-name".
        place.city = "Córdoba"
        place.country = Country('AR')
        for lang, country_name in {'en': "Argentina", 'eo': "Argentino"}.items():
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                self.assertEqual(str(place), f"Córdoba, {country_name}")

        # A place in an unknown city is expected to be "Country-name".
        place.city = ""
        place.country = Country('UY')
        for lang, country_name in {'en': "Uruguay", 'eo': "Urugvajo"}.items():
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                self.assertEqual(str(place), country_name)

        # A place in a known city is expected to be "City-name, Country-name".
        place.city = Faker._get_faker().city()
        place.country = Country('CL')
        self.assertEqual(str(place), f'{place.city}, {place.country.name}')

    def test_repr(self):
        place = self.basic_place
        self.assertSurrounding(repr(place), f"<Place #{place.pk}:", ">")

    def test_visibility_delete_protection(self):
        with self.assertRaises(ProtectedError):
            self.basic_place.visibility.delete()
        with self.assertRaises(ProtectedError):
            self.basic_place.family_members_visibility.delete()
        self.basic_place.refresh_from_db()
        self.assertIsNotNone(self.basic_place.visibility)
        self.assertIsNotNone(self.basic_place.family_members_visibility)

    def test_visible_externally(self):
        place = self.basic_place

        # Place is expected to be not visible if it was deleted.
        place.deleted_on = timezone.now()
        visible, reasons = place.is_visible_externally()
        self.assertFalse(visible)
        self.assertTrue(reasons["deleted"])

        # Place is expected to be not visible when it is hidden.
        place.deleted_on = None
        place.visibility.visible_online_public = False
        visible, reasons = place.is_visible_externally()
        self.assertFalse(visible)
        self.assertTrue(reasons["not accessible by users"])

        # Place is expected to be not visible if the owner disabled anonymous access.
        place.visibility.visible_online_public = True
        place.owner.pref.public_listing = False
        visible, reasons = place.is_visible_externally()
        self.assertFalse(visible)
        self.assertTrue(reasons["not accessible by visitors"])

        # Place is expected to be visible if none of the conditions are met.
        place.visibility.visible_online_public = True
        place.owner.pref.public_listing = True
        visible, reasons = place.is_visible_externally()
        self.assertTrue(visible)
        for reason_text, reason_value in reasons.items():
            with self.subTest(condition=reason_text):
                self.assertFalse(reason_value)

        # Place is expected to be not visible if the owner's profile is deleted.
        place.owner.deleted_on = timezone.now()
        visible, reasons = place.is_visible_externally()
        self.assertFalse(visible)
        self.assertTrue(reasons["owner is deleted"])

    def test_absolute_url(self):
        place = self.basic_place
        expected_urls = {
            'eo': '/ejo/{}/',
            'en': '/place/{}/',
        }
        for lang in expected_urls:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                self.assertEqual(
                    place.get_absolute_url(),
                    expected_urls[lang].format(place.pk)
                )

    def test_absolute_anonymous_url(self):
        place = self.basic_place
        expected_urls = {
            'eo': '/ejo/{}/',
            'en': '/place/{}/',
        }
        for lang in expected_urls:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                self.assertEqual(
                    place.get_absolute_anonymous_url(),
                    expected_urls[lang].format(place.pk)
                )
                self.assertEqual(
                    PlaceFactory._meta.model.get_absolute_anonymous_url_for_instance(place.pk),
                    expected_urls[lang].format(place.pk)
                )
