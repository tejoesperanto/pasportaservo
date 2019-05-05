from datetime import date

from django_countries.fields import Country
from django_webtest import WebTest
from factory import Faker

from ..factories import PlaceFactory


class PlaceModelTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.basic_place = PlaceFactory()

    def test_field_max_lengths(self):
        place = self.basic_place
        self.assertEquals(place._meta.get_field('city').max_length, 255)
        self.assertEquals(place._meta.get_field('closest_city').max_length, 255)
        self.assertEquals(place._meta.get_field('postcode').max_length, 11)
        self.assertEquals(place._meta.get_field('state_province').max_length, 70)
        self.assertEquals(place._meta.get_field('short_description').max_length, 140)

    def test_owner_available(self):
        # A place's owner who does not meet and does not guide is expected to be marked as unavailable.
        place = PlaceFactory.build(tour_guide=False, have_a_drink=False)
        self.assertFalse(place.owner_available)
        # A place's owner who meets but does not guide is expected to be marked as available.
        place = PlaceFactory.build(tour_guide=False, have_a_drink=True)
        self.assertTrue(place.owner_available)
        # A place's owner who does not meet but guides is expected to be marked as available.
        place = PlaceFactory.build(tour_guide=True, have_a_drink=False)
        self.assertTrue(place.owner_available)
        # A place's owner who both meets and guides is expected to be marked as available.
        place = PlaceFactory.build(tour_guide=True, have_a_drink=True)
        self.assertTrue(place.owner_available)

    def test_is_blocked(self):
        # A place without blocking dates is expected to be unblocked.
        place = PlaceFactory.build(blocked_from=None, blocked_until=None)
        self.assertFalse(place.is_blocked)

        # A place with blocking start date and without unblocking date is expected to be blocked.
        place = PlaceFactory.build(blocked_from=Faker('past_date'), blocked_until=None)
        self.assertTrue(place.is_blocked)
        place = PlaceFactory.build(blocked_from=date.today(), blocked_until=None)
        self.assertTrue(place.is_blocked)
        place = PlaceFactory.build(blocked_from=Faker('future_date'), blocked_until=None)
        self.assertTrue(place.is_blocked)

        # A place without blocking start date and with unblocking date in the past is expected to be unblocked.
        place = PlaceFactory.build(blocked_from=None, blocked_until=Faker('past_date'))
        self.assertFalse(place.is_blocked)
        # A place without blocking start date and with future unblocking date is expected to be blocked.
        place = PlaceFactory.build(blocked_from=None, blocked_until=date.today())
        self.assertTrue(place.is_blocked)
        place = PlaceFactory.build(blocked_from=None, blocked_until=Faker('future_date'))
        self.assertTrue(place.is_blocked)

        # A place with blocking dates in the past is expected to be unblocked.
        place = PlaceFactory.build(
            blocked_from=Faker('date_between', start_date='-2y', end_date='-1y'),
            blocked_until=Faker('date_between', start_date='-11M', end_date='-1d'))
        self.assertFalse(place.is_blocked)
        # A place with blocking start date in the past and with future unblocking date is expected to be blocked.
        place = PlaceFactory.build(
            blocked_from=Faker('date_between', start_date='-2y', end_date='-1y'),
            blocked_until=date.today())
        self.assertTrue(place.is_blocked)
        place = PlaceFactory.build(
            blocked_from=Faker('date_between', start_date='-2y', end_date='-1y'),
            blocked_until=Faker('future_date'))
        self.assertTrue(place.is_blocked)

        # A place with future blocking start date is expected to be blocked.
        place = PlaceFactory.build(blocked_from=date.today(), blocked_until=date.today())
        self.assertTrue(place.is_blocked)
        place = PlaceFactory.build(blocked_from=date.today(), blocked_until=Faker('future_date'))
        self.assertTrue(place.is_blocked)
        place = PlaceFactory.build(
            blocked_from=Faker('date_between', start_date='+1d', end_date='+11M'),
            blocked_until=Faker('date_between', start_date='+1y', end_date='+2y'))
        self.assertTrue(place.is_blocked)

    def test_locality_display(self):
        # A place in a known city is expected to be "City-name (Country-name)".
        place = PlaceFactory.build(city="Córdoba", country=Country('ES'))
        self.assertEqual(place.get_locality_display(), "Córdoba (Hispanio)")

        # A place in an unknown city is expected to be "Country-name".
        place = PlaceFactory.build(city="", country=Country('PT'))
        self.assertEqual(place.get_locality_display(), "Portugalio")

        # A place in a known city is expected to be "City-name (Country-name)".
        place = PlaceFactory.build(city=Faker('city'), country=Country('NL'))
        self.assertEqual(place.get_locality_display(), '{} ({})'.format(place.city, place.country.name))

    def test_str(self):
        # A place in a known city is expected to be "City-name, Country-name".
        place = PlaceFactory.build(city="Córdoba", country=Country('AR'))
        self.assertEqual(str(place), "Córdoba, Argentino")

        # A place in an unknown city is expected to be "Country-name".
        place = PlaceFactory.build(city="", country=Country('UY'))
        self.assertEqual(str(place), "Urugvajo")

        # A place in a known city is expected to be "City-name, Country-name".
        place = PlaceFactory.build(city=Faker('city'), country=Country('CL'))
        self.assertEqual(str(place), '{}, {}'.format(place.city, place.country.name))

    def test_absolute_url(self):
        place = self.basic_place
        self.assertEquals(
            place.get_absolute_url(),
            '/ejo/{}/'.format(place.pk)
        )
