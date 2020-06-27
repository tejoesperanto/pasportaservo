from collections import namedtuple
from datetime import datetime
from itertools import chain, islice
from unittest.mock import patch

from django.contrib.gis.geos import Point as GeoPoint
from django.core.exceptions import NON_FIELD_ERRORS
from django.test import override_settings, tag
from django.urls import reverse

from django_countries import Countries
from django_webtest import WebTest
from faker import Faker

from core.models import SiteConfiguration
from hosting.forms.places import PlaceForm
from hosting.models import LOCATION_CITY, Condition, Whereabouts
from maps import COUNTRIES_WITH_MANDATORY_REGION, SRID

from ..assertions import AdditionalAsserts
from ..factories import (
    ConditionFactory, PlaceFactory, ProfileFactory, WhereaboutsFactory,
)


@tag('forms', 'forms-place', 'place')
@override_settings(LANGUAGE_CODE='en')
class PlaceFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.config = SiteConfiguration.get_solo()
        cls.faker = Faker(locale='en-GB')
        cls.all_countries = Countries().countries.keys()
        cls.countries_no_mandatory_region = set(cls.all_countries) - set(COUNTRIES_WITH_MANDATORY_REGION)

        Condition.objects.all().delete()
        ConditionFactory.create_batch(20)
        cls.conditions = list(Condition.objects.values_list('id', flat=True))

        cls.expected_fields = {
            'country': ('random_element', {'elements': cls.all_countries}),
            'state_province': ('word', ),
            'city': ('word', ),
            'closest_city': ('word', ),
            'address': ('sentence', ),
            'postcode': ('postcode', ),
            'contact_before': ('pyint', ),
            'max_guest': ('pyint', ),
            'max_night': ('pyint', ),
            'short_description': ('text', {'max_nb_chars': 140}),
            'description': ('paragraph', {'nb_sentences': 3}),
            'available': ('pybool', ),
            'tour_guide': ('pybool', ),
            'have_a_drink': ('pybool', ),
            'sporadic_presence': ('pybool', ),
            'in_book': ('pyint', ),
            'conditions': ('random_elements', {'elements': cls.conditions, 'unique': True}),
        }
        cls.book_required_fields = [
            'country',
            'city',
            'closest_city',
            'address',
            'available',
        ]
        cls.location_fields = [
            'country',
            'state_province',
            'city',
            'postcode',
        ]

        cls.simple_place = PlaceFactory(available=False)
        cls.complete_place = PlaceFactory(
            country=cls.faker.random_element(elements=cls.countries_no_mandatory_region),
            available=False, tour_guide=False, have_a_drink=False,
            state_province=cls.faker.county(), postcode=cls.faker.postcode(),
            location_confidence=10,
            max_guest=123, max_night=456, contact_before=789,
        )

    DummyLocation = namedtuple('Location', 'point')
    DummyLocationWithConfidence = namedtuple('Location', 'point, confidence')

    def setUp(self):
        self.simple_place.refresh_from_db()
        self.complete_place.refresh_from_db()

    def _fake_value(self, field_name, faker=None):
        generator_name, generator_params = islice(chain(self.expected_fields[field_name], [{}]), 2)
        return getattr(faker or self.faker, generator_name)(**generator_params)

    def test_init(self):
        form_empty = PlaceForm()

        # Verify that the expected fields are part of the form.
        self.assertEquals(set(self.expected_fields.keys()), set(form_empty.fields))

        # Verify that fields are marked 'required'.
        for field in ('country',):
            with self.subTest(field=field):
                self.assertTrue(form_empty.fields[field].required)

    def test_blank_data(self):
        # Empty form is expected to be invalid.
        form = PlaceForm({})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'country': ["This field is required."]})

        # Empty form for a place in book is expected to be invalid.
        form = PlaceForm({'in_book': True})
        self.assertFalse(form.is_valid())
        self.assertEqual(set(form.errors.keys()), set(self.book_required_fields + [NON_FIELD_ERRORS]))
        for field in self.book_required_fields:
            with self.subTest(condition="in book", field=field):
                self.assertEqual(
                    form.errors[field],
                    ["This field is required to be printed in the book."
                     if field != 'country' else "This field is required."]
                )
            assert_content = "You want to be in the printed edition"
            assert_message = (
                "Form error does not include clarification about book requirements.\n"
                f"\n\tExpected to see: {assert_content}"
                f"\n\tBut saw instead: {form.errors[NON_FIELD_ERRORS]!r}"
            )
            self.assertTrue(
                any(assert_content in error for error in form.errors[NON_FIELD_ERRORS]), msg=assert_message
            )

    def test_invalid_country(self):
        form = PlaceForm({'country': ""})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'country': ["This field is required."]})

        form = PlaceForm({'country': "ZZ"})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'country': ["Select a valid choice. ZZ is not one of the available choices."]})

    def test_invalid_province(self):
        # Form data of country without provinces and of empty province is expected to be valid.
        form = PlaceForm({
            'country': self.faker.random_element(elements=self.countries_no_mandatory_region),
        })
        self.assertTrue(form.is_valid())
        # Form data of country with provinces and of empty province is expected to be invalid.
        form = PlaceForm({
            'country': self.faker.random_element(elements=COUNTRIES_WITH_MANDATORY_REGION),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('state_province', form.errors)
        self.assertTrue(any("the name of the state or province must be indicated" in error
                            for error in form.errors['state_province']))

    def test_valid_province(self):
        # Form data of country with provinces and of indicated province is expected to be valid.
        form = PlaceForm({
            'country': self.faker.random_element(elements=COUNTRIES_WITH_MANDATORY_REGION),
            'state_province': self.faker.word(),  # No restrictions are implemnted yet...
        })
        self.assertTrue(form.is_valid())

    def test_invalid_city_when_hosting_meeting(self):
        test_combinations = [
            ('available', ),
            ('have_a_drink', ),
            ('tour_guide', ),
            ('available', 'have_a_drink', ),
            ('available', 'tour_guide', ),
            ('have_a_drink', 'tour_guide', ),
        ]

        # Form data with missing city name when user is hosting or meeting, is expected to be invalid.
        for field_names in test_combinations:
            with self.subTest(offer=' / '.join(field_names)):
                form = PlaceForm(
                    dict(
                        country=self.simple_place.country,
                        city="",
                        **{field: True for field in field_names},
                    ),
                    instance=self.simple_place)
                self.assertFalse(form.is_valid())
                self.assertIn('city', form.errors)
                if 'available' in field_names:
                    self.assertEqual(form.errors['city'], ["This field is required if you accept guests."])
                else:
                    self.assertEqual(form.errors['city'], ["This field is required if you meet visitors."])

    def test_invalid_address_when_hosting(self):
        # Form data with missing nearest city name or address, when user is hosting, is expected to be invalid.
        for field_name in ('closest_city', 'city', 'address'):
            with self.subTest(offer='available', field=field_name):
                form = PlaceForm(
                    {
                        'country': self.simple_place.country,
                        field_name: "",
                        'available': True,
                    },
                    instance=self.simple_place)
                self.assertFalse(form.is_valid())
                self.assertIn(field_name, form.errors)
                self.assertEqual(form.errors[field_name], ["This field is required if you accept guests."])

    def test_invalid_age(self):
        owner = ProfileFactory(birth_date=self.faker.date_this_decade())
        place = PlaceFactory(owner=owner)
        test_combinations = [
            ('available', ),
            ('have_a_drink', ),
            ('tour_guide', ),
            ('available', 'have_a_drink', ),
            ('available', 'tour_guide', ),
            ('have_a_drink', 'tour_guide', ),
        ]

        # Form submission with valid data but for an overly young user
        # who wants to host or meet, is expected to raise an error.
        for field_names in test_combinations:
            with self.subTest(offer=' / '.join(field_names), age=owner.age):
                form = PlaceForm(
                    dict(
                        country=place.country,
                        city=place.city,
                        closest_city=place.closest_city,
                        address=place.address,
                        **{field: True for field in field_names},
                    ),
                    instance=place)
                self.assertFalse(form.is_valid())
                if 'available' in field_names:
                    self.assertIn('available', form.errors)
                    for field_name in set(field_names) - set(['available']):
                        self.assertNotIn(field_name, form.errors)
                    error_message = (
                        "The minimum age to be allowed hosting is {}.".format(self.config.host_min_age)
                    )
                else:
                    for field_name in field_names:
                        self.assertIn(field_name, form.errors)
                    error_message = (
                        "The minimum age to be allowed meeting with visitors is {}.".format(self.config.meet_min_age)
                    )
                self.assertEqual(form.errors[NON_FIELD_ERRORS], [error_message])

    @patch('hosting.forms.places.geocode')
    @patch('hosting.forms.places.geocode_city')
    def test_save_no_change(self, mock_geocode_city, mock_geocode):
        form = PlaceForm(instance=self.simple_place)  # = GET
        form = PlaceForm(data=form.initial.copy(), instance=self.simple_place)  # = POST
        # No change in data means that the form is expected to be valid.
        self.assertTrue(form.is_valid())
        # The geocoding utility is not expected to be called, because place already has a location.
        mock_geocode.side_effect = AssertionError("geocode was unexpectedly called")
        mock_geocode_city.side_effect = AssertionError("geocode-city was unexpectedly called")
        number_coded_cities = Whereabouts.objects.count()
        place = form.save(commit=False)
        # The number of geocoded cities is expected to remain the same.
        self.assertEqual(Whereabouts.objects.count(), number_coded_cities)
        # The form is expected to have an attribute 'confidence' equal to location confidence.
        self.assertEqual(place.location, self.simple_place.location)
        self.assertTrue(hasattr(form, 'confidence'))
        self.assertEqual(form.confidence, self.simple_place.location_confidence)

    @patch('hosting.forms.places.geocode')
    @patch('hosting.forms.places.geocode_city')
    def test_save_change_non_location_data(self, mock_geocode_city, mock_geocode):
        form = PlaceForm(instance=self.complete_place)  # = GET
        form_data = form.initial.copy()
        number_coded_cities = Whereabouts.objects.count()

        for field_name in ('short_description', 'description',
                           'max_guest', 'max_night', 'contact_before', 'sporadic_presence',
                           'tour_guide', 'have_a_drink', 'conditions'):
            for field_empty in (False, True):
                data = form_data.copy()
                if not field_empty:
                    data[field_name] = self._fake_value(field_name)
                else:
                    data[field_name] = None
                with self.subTest(field=field_name, has_value='✓ ' if not field_empty else '✗ '):
                    self.complete_place.refresh_from_db()
                    form = PlaceForm(data=data, instance=self.complete_place)
                    self.assertTrue(form.is_valid(), msg=repr(form.errors))

                    # The geocoding utility is not expected to be called, because location data has not changed.
                    mock_geocode.side_effect = AssertionError("geocode was unexpectedly called")
                    mock_geocode_city.side_effect = AssertionError("geocode-city was unexpectedly called")
                    place = form.save(commit=False)
                    # The number of geocoded cities is expected to remain the same.
                    self.assertEqual(Whereabouts.objects.count(), number_coded_cities)
                    # The form is expected to have an attribute 'confidence' equal to location confidence.
                    self.assertEqual(place.location, self.complete_place.location)
                    self.assertTrue(hasattr(form, 'confidence'))
                    self.assertEqual(form.confidence, place.location_confidence)

    @patch('hosting.forms.places.geocode')
    @patch('hosting.forms.places.geocode_city')
    def test_save_change_location_data(self, mock_geocode_city, mock_geocode):
        form = PlaceForm(instance=self.complete_place)  # = GET
        form_data = form.initial.copy()
        test_point = GeoPoint([-21.932887, 64.150438], srid=SRID)
        test_assertion = AssertionError("geocode was not supposed to be called second time")
        test_config = [
            ([None, test_assertion], None, 0),
            ([self.DummyLocation(None), test_assertion], None, 0),
            ([self.DummyLocationWithConfidence(test_point, 1), test_assertion], None, 0),
            ([self.DummyLocationWithConfidence(test_point, 6), test_assertion], test_point, 6),
        ]
        mock_geocode_city.return_value = None
        number_coded_cities = Whereabouts.objects.count()

        for field_name in self.location_fields:
            for field_empty in (False, True):
                data = form_data.copy()
                if field_name == 'country':
                    # Ensure that the value of the country field is indeed changed.
                    remaining_countries = self.countries_no_mandatory_region - set([data['country']])
                    data[field_name] = self.faker.random_element(elements=remaining_countries)
                else:
                    data[field_name] = self._fake_value(field_name) if not field_empty else None
                for i, (side_effect, expected_loc, expected_loc_confidence) in enumerate(test_config):
                    with self.subTest(
                            field=field_name,
                            has_value='✓ ' if not field_empty else '✗ ',
                            value=data[field_name],
                            prev_value=form_data[field_name],
                            test_case=i):
                        self.complete_place.refresh_from_db()
                        form = PlaceForm(data=data, instance=self.complete_place)
                        self.assertTrue(form.is_valid(), msg=repr(form.errors))

                        mock_geocode.return_value = None
                        mock_geocode.side_effect = side_effect
                        place = form.save(commit=False)
                        # The number of geocoded cities is expected to remain the same.
                        self.assertEqual(Whereabouts.objects.count(), number_coded_cities)
                        # The form is expected to have an attribute 'confidence' equal to location confidence.
                        self.assertEqual(place.location, expected_loc)
                        self.assertEqual(place.location_confidence, expected_loc_confidence)
                        self.assertTrue(hasattr(form, 'confidence'))
                        self.assertEqual(form.confidence, place.location_confidence)

    @patch('hosting.forms.places.geocode')
    @patch('hosting.forms.places.geocode_city')
    def test_save_change_location_data_and_address(self, mock_geocode_city, mock_geocode):
        form = PlaceForm(instance=self.complete_place)  # = GET
        form_data = form.initial.copy()
        test_point_A = GeoPoint([-21.932887, 64.150438], srid=SRID)
        test_point_B = GeoPoint([-22.094971, 64.308326], srid=SRID)
        test_assertion = AssertionError("geocode was not supposed to be called second time")
        test_config = [
            ([None, test_assertion], None, 0),
            ([self.DummyLocation(None), self.DummyLocation(None)], None, 0),
            ([self.DummyLocation(None), self.DummyLocationWithConfidence(test_point_B, 1)], None, 0),
            ([self.DummyLocation(None), self.DummyLocationWithConfidence(test_point_B, 6)], test_point_B, 6),
            (
                [
                    self.DummyLocationWithConfidence(test_point_A, 1),
                    self.DummyLocationWithConfidence(test_point_B, 1),
                ], None, 0
            ),
            (
                [
                    self.DummyLocationWithConfidence(test_point_A, 1),
                    self.DummyLocationWithConfidence(test_point_B, 7),
                ], None, 0
            ),
            ([self.DummyLocationWithConfidence(test_point_A, 8), test_assertion], test_point_A, 8),
        ]
        mock_geocode_city.return_value = None
        number_coded_cities = Whereabouts.objects.count()

        for field_name in self.location_fields:
            for field_empty in (False, True):
                data = form_data.copy()
                if field_name == 'country':
                    # Ensure that the value of the country field is indeed changed.
                    remaining_countries = self.countries_no_mandatory_region - set([data['country']])
                    data[field_name] = self.faker.random_element(elements=remaining_countries)
                else:
                    data[field_name] = self._fake_value(field_name) if not field_empty else None
                data['address'] = getattr(self.faker, self.expected_fields['address'][0])()
                for i, (side_effect, expected_loc, expected_loc_confidence) in enumerate(test_config):
                    with self.subTest(
                            field=field_name,
                            has_value='✓ ' if not field_empty else '✗ ',
                            value=data[field_name],
                            prev_value=form_data[field_name],
                            test_case=i):
                        self.complete_place.refresh_from_db()
                        form = PlaceForm(data=data, instance=self.complete_place)
                        self.assertTrue(form.is_valid(), msg=repr(form.errors))

                        mock_geocode.return_value = None
                        mock_geocode.side_effect = side_effect
                        place = form.save(commit=False)
                        # The number of geocoded cities is expected to remain the same.
                        self.assertEqual(Whereabouts.objects.count(), number_coded_cities)
                        # The form is expected to have an attribute 'confidence' equal to location confidence.
                        self.assertEqual(place.location, expected_loc)
                        self.assertEqual(place.location_confidence, expected_loc_confidence)
                        self.assertTrue(hasattr(form, 'confidence'))
                        self.assertEqual(form.confidence, place.location_confidence)

    @patch('hosting.forms.places.geocode')
    @patch('hosting.forms.places.geocode_city')
    def test_save_geocode_existing_city(self, mock_geocode_city, mock_geocode):
        # We don't care about geocoding the address of the place.
        mock_geocode.return_value = None
        # But we do care whether the geocoding of the city is done or not.
        mock_geocode_city.side_effect = AssertionError("geocode-city was unexpectedly called")

        for province in ("mandatory", "not mandatory"):
            if province == "mandatory":
                countries = set(COUNTRIES_WITH_MANDATORY_REGION)
            else:
                countries = self.countries_no_mandatory_region
            country = self.faker.random_element(elements=countries)
            whereabouts = WhereaboutsFactory(type=LOCATION_CITY, country=country)
            number_coded_cities = Whereabouts.objects.count()

            form_data = PlaceForm(instance=self.simple_place).initial.copy()
            form_data['country'] = whereabouts.country
            if province == "mandatory":
                form_data['state_province'] = whereabouts.state.lower()
            else:
                form_data['state_province'] = self._fake_value('state_province')

            for field_empty in (False, True):
                form_data['city'] = whereabouts.name.lower() if not field_empty else ""
                with self.subTest(state_province=province, city_has_value='✓ ' if not field_empty else '✗ '):
                    self.simple_place.refresh_from_db()
                    form = PlaceForm(data=form_data, instance=self.simple_place)
                    self.assertTrue(form.is_valid(), msg=repr(form.errors))
                    form.save(commit=False)
                    # The number of geocoded cities is expected to remain the same.
                    self.assertEqual(Whereabouts.objects.count(), number_coded_cities)

    @patch('hosting.forms.places.geocode')
    @patch('hosting.forms.places.geocode_city')
    def test_save_geocode_new_city(self, mock_geocode_city, mock_geocode):
        # We don't care about geocoding the address of the place.
        mock_geocode.return_value = None
        number_coded_cities = Whereabouts.objects.count()
        GeoResult = namedtuple('GeoResult', 'xy, bbox')

        for province in ("mandatory", "not mandatory"):
            for field_empty in (False, True):
                self.simple_place.refresh_from_db()
                form_data = PlaceForm(instance=self.simple_place).initial.copy()
                if province == "mandatory":
                    form_data['country'] = self.faker.random_element(elements=COUNTRIES_WITH_MANDATORY_REGION)
                    form_data['state_province'] = self._fake_value('state_province')
                else:
                    form_data['country'] = self.faker.random_element(elements=self.countries_no_mandatory_region)
                    form_data['state_province'] = self._fake_value('state_province') if not field_empty else ""
                if not field_empty:
                    # Make sure the value is unique.
                    form_data['city'] = "{}_{}".format(self._fake_value('city'), datetime.now().timestamp())
                    mock_geocode_city.return_value = GeoResult(
                        [35.304816, 32.706630],
                        {'northeast': [35.313535, 32.736300], 'southwest': [35.266052, 32.672766]})
                    mock_geocode_city.side_effect = None
                else:
                    form_data['city'] = ""
                    mock_geocode_city.return_value = None
                    mock_geocode_city.side_effect = AssertionError("geocode-city was unexpectedly called")

                with self.subTest(state_province=province, city_has_value='✓ ' if not field_empty else '✗ '):
                    form = PlaceForm(data=form_data, instance=self.simple_place)
                    self.assertTrue(form.is_valid(), msg=repr(form.errors))
                    form.save(commit=False)
                    if field_empty:
                        # The number of geocoded cities is expected to remain the same.
                        self.assertEqual(Whereabouts.objects.count(), number_coded_cities)
                    else:
                        # The number of geocoded cities is expected to change by 1 when a new city is supplied.
                        self.assertEqual(Whereabouts.objects.count(), number_coded_cities + 1)
                        number_coded_cities += 1
                        whereabouts = Whereabouts.objects.order_by('-id')[0]
                        self.assertEqual(whereabouts.country, form_data['country'])
                        self.assertEqual(whereabouts.name, form_data['city'].upper())
                        self.assertEqual(whereabouts.center, [35.304816, 32.706630])

    def test_valid_data(self):
        faker = Faker(locale='el')
        test_dataset = {
            "partial": ('country', 'state_province', 'city', 'closest_city', 'address'),
            "full": self.expected_fields.keys(),
        }

        for dataset_type in test_dataset:
            with self.subTest(dataset=dataset_type):
                data = {
                    field: self._fake_value(field, faker)
                    for field in test_dataset[dataset_type]
                }
                if data.get('in_book'):
                    data['available'] = True
                form = PlaceForm(data, instance=self.simple_place)
                self.assertTrue(form.is_valid())

    def test_view_page(self):
        page = self.app.get(
            reverse('place_update', kwargs={'pk': self.simple_place.pk}),
            user=self.simple_place.owner.user,
        )
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], PlaceForm)

    @patch('hosting.forms.places.geocode')
    @patch('hosting.forms.places.geocode_city')
    def test_form_submit(self, mock_geocode_city, mock_geocode):
        mock_geocode.return_value = None
        mock_geocode_city.return_value = None

        # Submission of a form with modified non-location related fields is expected
        # to be successful and result in redirection to the profile view page.
        page = self.app.get(
            reverse('place_update', kwargs={'pk': self.complete_place.pk}),
            user=self.complete_place.owner.user,
        )
        faker = Faker(locale='zh')
        data = {}
        for field_name in ('short_description', 'sporadic_presence', 'conditions'):
            page.form[field_name] = data[field_name] = self._fake_value(field_name, faker)
        page = page.form.submit()
        self.complete_place.refresh_from_db()
        self.assertRedirects(
            page,
            '{}#p{}'.format(
                reverse('profile_edit', kwargs={
                    'pk': self.complete_place.owner.pk,
                    'slug': self.complete_place.owner.autoslug}),
                self.complete_place.pk,
            )
        )
        self.assertEqual(self.complete_place.short_description, data['short_description'])
        self.assertEqual(self.complete_place.sporadic_presence, data['sporadic_presence'])
        self.assertEqual(set(self.complete_place.conditions.values_list('id', flat=True)), set(data['conditions']))

        # Submission of a form with modified location-related fields is expected
        # to be successful and result in redirection to the location update form page.
        page = self.app.get(
            reverse('place_update', kwargs={'pk': self.complete_place.pk}),
            user=self.complete_place.owner.user,
        )
        for field_name in ('address', 'state_province'):
            page.form[field_name] = data[field_name] = self._fake_value(field_name, faker)
        page = page.form.submit()
        self.complete_place.refresh_from_db()
        self.assertRedirects(
            page,
            reverse('place_location_update', kwargs={'pk': self.complete_place.pk})
        )
        self.assertEqual(self.complete_place.address, data['address'])
        self.assertEqual(self.complete_place.state_province, data['state_province'])
        self.assertEqual(self.complete_place.location, None)
        self.assertEqual(self.complete_place.location_confidence, 0)
