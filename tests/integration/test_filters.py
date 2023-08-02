from django.test import TestCase, tag
from django.utils import timezone

from django_filters import BooleanFilter, CharFilter

from hosting.filters.search import (
    ModelMultipleChoiceIncludeExcludeFilter,
    NumberOrNoneFilter, SearchFilterSet,
)
from hosting.forms.listing import SearchForm
from hosting.models import Place

from ..factories import PlaceFactory, ProfileFactory


@tag('integration')
class SearchFilterSetTests(TestCase):
    def test_init(self):
        filterset = SearchFilterSet()

        # Verify that the expected filters are part of the filterset.
        expected_filters = """
            max_guest max_night contact_before tour_guide have_a_drink
            owner__first_name owner__last_name available conditions
        """.split()
        self.assertEqual(set(expected_filters), set(filterset.filters))

        # Verify that the correct filter classes are applied to the filters.
        self.assertIs(type(filterset.filters['max_guest']), NumberOrNoneFilter)
        self.assertIs(type(filterset.filters['max_night']), NumberOrNoneFilter)
        self.assertIs(type(filterset.filters['contact_before']), NumberOrNoneFilter)
        self.assertIs(type(filterset.filters['tour_guide']), BooleanFilter)
        self.assertIs(type(filterset.filters['have_a_drink']), BooleanFilter)
        self.assertIs(type(filterset.filters['owner__first_name']), CharFilter)
        self.assertIs(type(filterset.filters['owner__last_name']), CharFilter)
        self.assertIs(type(filterset.filters['available']), BooleanFilter)
        self.assertIs(type(filterset.filters['conditions']), ModelMultipleChoiceIncludeExcludeFilter)

        # Verify the comparison operations performed by numeric filters.
        self.assertEqual(filterset.filters['max_guest'].lookup_expr, 'gte')
        self.assertEqual(filterset.filters['max_night'].lookup_expr, 'gte')
        self.assertEqual(filterset.filters['contact_before'].lookup_expr, 'lte')

        # Verify defaults.
        self.assertIsNotNone(filterset.data)
        self.assertTrue(filterset.data.get('available', None))

    def test_form(self):
        filterset = SearchFilterSet()
        self.assertIs(filterset._meta.form, SearchForm)
        form_class = filterset.get_form_class()
        self.assertTrue(issubclass(form_class, SearchForm))
        form = form_class()
        self.assertTrue(hasattr(form, 'model'))
        self.assertIs(form.model, Place)

    def test_filtering(self):
        profile = ProfileFactory()
        p1 = PlaceFactory(owner=profile, max_night=10)
        p2 = PlaceFactory(owner=profile, deleted_on=timezone.now())  # noqa: F841
        p3 = PlaceFactory(owner=profile, max_night=4)
        p4 = PlaceFactory(owner=profile, max_night=None, have_a_drink=True)
        p5 = PlaceFactory(owner=profile, available=False)
        qs = Place.objects.all()

        f = SearchFilterSet(queryset=qs)
        self.assertQuerysetEqual(f.qs, [p1.pk, p3.pk, p4.pk], lambda o: o.pk, ordered=False)
        f = SearchFilterSet({'max_night': 5}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [p4.pk, p5.pk, p1.pk], lambda o: o.pk, ordered=False)


@tag('integration')
class PlaceFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile_one = ProfileFactory()
        cls._setUpPlace(
            owner=cls.profile_one,
            available=True, tour_guide=False, have_a_drink=False, in_book=False,
            visibility={'online_public': True, 'in_book': False})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=True, tour_guide=True, have_a_drink=True, in_book=True,
            deleted_on=timezone.now(),
            visibility={'online_public': True, 'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=False, tour_guide=False, have_a_drink=False, in_book=True,
            visibility={'online_public': True, 'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=True, tour_guide=False, have_a_drink=False, in_book=False,
            visibility={'online_public': False, 'in_book': False})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=True, tour_guide=True, have_a_drink=False, in_book=False,
            visibility={'online_public': False, 'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=True, tour_guide=False, have_a_drink=True, in_book=False,
            visibility={'online_public': False, 'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=False, tour_guide=True, have_a_drink=False, in_book=False,
            visibility={'online_public': False, 'in_book': False})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=False, tour_guide=False, have_a_drink=True, in_book=False,
            visibility={'online_public': False, 'in_book': False})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=True, tour_guide=False, have_a_drink=False, in_book=True,
            visibility={'online_public': False, 'in_book': False})
        cls._setUpPlace(
            owner=cls.profile_one,
            available=True, tour_guide=False, have_a_drink=False, in_book=True,
            visibility={'online_public': False, 'in_book': True})

        cls.profile_two = ProfileFactory()
        cls._setUpPlace(
            owner=cls.profile_two,
            available=True, in_book=True, confirmed_on=None, checked_on=None,
            visibility={'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_two,
            available=True, in_book=True, confirmed_on=timezone.now(), checked_on=None,
            visibility={'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_two,
            available=True, in_book=True, confirmed_on=timezone.now(), checked_on=None,
            deleted_on=timezone.now(),
            visibility={'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_two,
            available=True, in_book=True, confirmed_on=timezone.now(), checked_on=timezone.now(),
            visibility={'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_two,
            available=True, in_book=True, confirmed_on=None, checked_on=timezone.now(),
            visibility={'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_two,
            available=True, in_book=True, confirmed_on=None, checked_on=timezone.now(),
            visibility={'in_book': True})
        cls._setUpPlace(
            owner=cls.profile_two,
            available=True, in_book=True, confirmed_on=None, checked_on=timezone.now(),
            deleted_on=timezone.now(),
            visibility={'in_book': True})

    @classmethod
    def _setUpPlace(cls, **kwargs):
        visibility = kwargs.pop('visibility', {})
        place = PlaceFactory(**kwargs)
        place.visibility.refresh_from_db()
        for key, value in visibility.items():
            place.visibility[key] = value
        place.visibility.save()
        return place

    def test_invalid_attribute(self):
        with self.assertRaises(AttributeError) as cm:
            self.profile_one.gerrit()
        self.assertEqual(str(cm.exception), "Attribute gerrit does not exist on model Profile")

    def test_invalid_lookup(self):
        with self.assertRaises(AttributeError) as cm:
            self.profile_one.is_quacking()
        self.assertEqual(str(cm.exception), "Query 'quacking' is not implemented for model Profile")

        with self.assertRaises(AttributeError) as cm:
            self.profile_one.has_places_for_quacking()
        self.assertEqual(str(cm.exception), "Query 'quacking' is not implemented for model Profile")

    def test_hosting_filter(self):
        self.assertEqual(self.profile_one.is_hosting, 1)
        # The results are expected to be cached.
        with self.assertNumQueries(0):
            self.assertEqual(self.profile_one.is_hosting, 1)
        self.assertEqual(self.profile_one.has_places_for_hosting, 6)
        # The results are expected to be cached.
        with self.assertNumQueries(0):
            self.assertEqual(self.profile_one.has_places_for_hosting, 6)

    def test_meeting_filter(self):
        self.assertEqual(self.profile_one.is_meeting, 0)
        # The results are expected to be cached.
        with self.assertNumQueries(0):
            self.assertEqual(self.profile_one.is_meeting, 0)
        self.assertEqual(self.profile_one.has_places_for_meeting, 4)
        # The results are expected to be cached.
        with self.assertNumQueries(0):
            self.assertEqual(self.profile_one.has_places_for_meeting, 4)

    def test_accepting_guests_filter(self):
        self.assertEqual(self.profile_one.is_accepting_guests, 1)
        # The results are expected to be cached.
        with self.assertNumQueries(0):
            self.assertEqual(self.profile_one.is_accepting_guests, 1)
        self.assertEqual(self.profile_one.has_places_for_accepting_guests, 8)
        # The results are expected to be cached.
        with self.assertNumQueries(0):
            self.assertEqual(self.profile_one.has_places_for_accepting_guests, 8)

    def test_in_book_filter(self):
        self.assertEqual(self.profile_one.is_in_book, 1)
        # The results are expected to be cached.
        with self.assertNumQueries(0):
            self.assertEqual(self.profile_one.is_in_book, 1)
        self.assertEqual(self.profile_one.has_places_for_in_book, 2)
        # The results are expected to be cached.
        with self.assertNumQueries(0):
            self.assertEqual(self.profile_one.has_places_for_in_book, 2)

    def test_ok_for_book_filter(self):
        self.assertEqual(self.profile_one.is_ok_for_book(), 0)
        self.assertEqual(self.profile_one.has_places_for_ok_for_book(), 0)
        # We do not test for caching because there is no such requirement.
        self.assertEqual(
            self.profile_one.is_ok_for_book(accept_confirmed=False, accept_approved=False),
            1)
        # The 'has_places_for_ok_for_book' filter is not implemented and is
        # expected to return the same result as the 'is_ok_for_book' filter.
        self.assertEqual(
            self.profile_one.has_places_for_ok_for_book(accept_confirmed=False, accept_approved=False),
            1)

        self.assertEqual(
            self.profile_two.is_ok_for_book(accept_confirmed=False, accept_approved=False),
            5)
        self.assertEqual(
            self.profile_two.is_ok_for_book(accept_confirmed=True, accept_approved=False),
            2)
        self.assertEqual(
            self.profile_two.is_ok_for_book(accept_confirmed=False, accept_approved=True),
            3)
        self.assertEqual(
            self.profile_two.is_ok_for_book(accept_confirmed=True, accept_approved=True),
            4)
        # The default params of the filter are expected to be confirmed=False, approved=True.
        self.assertEqual(self.profile_two.is_ok_for_book(), 3)
