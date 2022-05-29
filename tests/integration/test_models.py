from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.test import TestCase, override_settings, tag
from django.utils import timezone

from factory import Faker

from hosting.models import CountryRegion, FamilyMember, Place, Profile

from ..factories import (
    ConditionFactory, CountryRegionFactory, PhoneFactory, PlaceFactory,
    ProfileFactory, ProfileSansAccountFactory, UserFactory,
)


@tag('integration')
class ProfileModelIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = ProfileFactory()

        cls.phones = PhoneFactory.build_batch(3, profile=cls.profile)
        cls.phones[1].deleted_on = timezone.now()
        for phone in cls.phones:
            phone.save()
        cls.profile.set_phone_order([cls.phones[i].pk for i in (1, 2, 0)])
        for phone in cls.phones:
            phone.refresh_from_db()

        cls.places = PlaceFactory.build_batch(4, owner=cls.profile)
        cls.places[2].deleted_on = cls.places[3].deleted_on = timezone.now()
        cls.places[1].in_book = cls.places[3].in_book = True
        for place in cls.places:
            place.save()

    def test_rawdisplay(self):
        self.assertEqual(
            self.profile.rawdisplay_phones(),
            f"{self.phones[2].rawdisplay()}, {self.phones[0].rawdisplay()}"
        )

    def test_confirmation(self):
        # The `places_confirmed` attribute looks at all profile's places
        # marked for printing in book which are not deleted, and is
        # expected to be False.
        self.assertFalse(self.profile.places_confirmed)

        # The `confirm_all_info` method is expected to mark the profile's
        # all non-deleted associated places and phones as confirmed.
        all_objects = [self.profile] + self.phones + self.places
        for obj in all_objects:
            self.assertIsNone(obj.confirmed_on)
        self.profile.confirm_all_info()
        for obj in all_objects:
            obj.refresh_from_db()
            with self.subTest(obj=obj._meta.model_name, deleted=bool(obj.deleted_on)):
                if obj.deleted_on:
                    # A deleted object is expected to be not confirmed.
                    self.assertIsNone(obj.confirmed_on)
                else:
                    # An active object is expected to be confirmed.
                    self.assertIsNotNone(obj.confirmed_on)
        # The method is expected to be protected in templates.
        self.assertTrue(hasattr(self.profile.confirm_all_info, 'alters_data'))
        self.assertTrue(getattr(self.profile.confirm_all_info, 'alters_data'))

        # The profile's places for printing are expected to be confirmed
        # after invoking `confirm_all_info`.
        self.assertTrue(self.profile.places_confirmed)

        # Unconfirming is expected to mark the profile's all non-deleted
        # associated objects as not confirmed.
        self.profile.confirm_all_info(False)
        for obj in all_objects:
            obj.refresh_from_db()
            with self.subTest(obj=obj._meta.model_name, deleted=bool(obj.deleted_on)):
                self.assertIsNone(obj.confirmed_on)

    def mark_emails_as_invalid_tests(self, email, params, expected_updated, expected_marked):
        with self.subTest(params=params, updated=expected_updated, mark="invalid"):
            result = self.profile.mark_invalid_emails(params)
            self.profile.refresh_from_db()
            self.profile.user.refresh_from_db()

            with self.subTest(
                    user_email=self.profile.user.email,
                    profile_email=self.profile.email):
                # Verify the operation on the profile's email.
                if not expected_updated or not expected_updated['p']:
                    self.assertEqual(self.profile.email, "")
                    self.assertEqual(result[self.profile._meta.model], 0)
                else:
                    self.assertTrue(self.profile.email.startswith(settings.INVALID_PREFIX))
                    self.assertEqual(self.profile.email.count(settings.INVALID_PREFIX), 1)
                    self.assertEqual(
                        result[self.profile._meta.model],
                        1 if expected_marked['p'] else 0
                    )
                # Verify the operation on the account's email.
                if not expected_updated or not expected_updated['u']:
                    self.assertEqual(self.profile.user.email, email)
                    self.assertEqual(result[self.profile.user._meta.model], 0)
                else:
                    self.assertTrue(self.profile.user.email.startswith(settings.INVALID_PREFIX))
                    self.assertTrue(self.profile.user.email.endswith(email))
                    self.assertEqual(self.profile.user.email.count(settings.INVALID_PREFIX), 1)
                    self.assertEqual(
                        result[self.profile.user._meta.model],
                        1 if expected_marked['u'] else 0
                    )

    def mark_emails_as_valid_tests(self, email, params, expected_updated, expected_unmarked):
        with self.subTest(params=params, updated=expected_updated, mark="valid"):
            result = self.profile.mark_valid_emails(params)
            invalid_email = f'{settings.INVALID_PREFIX}{email}'
            self.profile.refresh_from_db()
            self.profile.user.refresh_from_db()

            with self.subTest(
                    user_email=self.profile.user.email,
                    profile_email=self.profile.email):
                # Verify the operation on the profile's email.
                if not expected_updated or not expected_updated['p']:
                    self.assertEqual(self.profile.email, invalid_email)
                    self.assertEqual(result[self.profile._meta.model], 0)
                else:
                    self.assertFalse(self.profile.email.startswith(settings.INVALID_PREFIX))
                    self.assertEqual(self.profile.email.count(settings.INVALID_PREFIX), 0)
                    self.assertEqual(
                        result[self.profile._meta.model],
                        1 if expected_unmarked['p'] else 0
                    )
                # Verify the operation on the account's email.
                if not expected_updated or not expected_updated['u']:
                    self.assertEqual(self.profile.user.email, invalid_email)
                    self.assertEqual(result[self.profile.user._meta.model], 0)
                else:
                    self.assertFalse(self.profile.user.email.startswith(settings.INVALID_PREFIX))
                    self.assertEqual(self.profile.user.email.count(settings.INVALID_PREFIX), 0)
                    self.assertEqual(self.profile.user.email, email)
                    self.assertEqual(
                        result[self.profile.user._meta.model],
                        1 if expected_unmarked['u'] else 0
                    )

    @override_settings(INVALID_PREFIX='BAD_DATA::')
    def test_mark_emails(self):
        self.assertEqual(self.profile.email, "")
        self.assertNotEqual(self.profile.user.email, "")
        email = self.profile.user.email
        invalid_email = f'{settings.INVALID_PREFIX}{email}'
        User = get_user_model()

        # The `mark_invalid_emails` method invoked with no parameters
        # is not expected to change anything.
        self.mark_emails_as_invalid_tests(
            email, None,
            expected_updated=False, expected_marked=False)
        # The method invoked with an empty list
        # is not expected to change anything.
        self.mark_emails_as_invalid_tests(
            email, [],
            expected_updated=False, expected_marked=False)
        # The method invoked with a non-existing email parameter
        # is not expected to change anything.
        self.mark_emails_as_invalid_tests(
            email, ["a@b.co"],
            expected_updated=False, expected_marked=False)
        # The method is expected to add the marker prefix to non-empty
        # emails of the profile and the user.
        self.mark_emails_as_invalid_tests(
            email, [email, ''],
            expected_updated={'u': True, 'p': False}, expected_marked={'u': True, 'p': False})
        # Repeating the operation is not expected to add one more prefix.
        self.mark_emails_as_invalid_tests(
            email, [email, ''],
            expected_updated={'u': True, 'p': False}, expected_marked={'u': False, 'p': False})
        # The method is expected to update only the corresponding object
        # if email addresses differ for the profile and the user.
        User.objects.filter(pk=self.profile.user.pk).update(email=email)
        Profile.all_objects.filter(pk=self.profile.pk).update(email="a.b.c@d.e.f.mx")
        self.mark_emails_as_invalid_tests(
            email, ["a.b.c@d.e.f.mx"],
            expected_updated={'u': False, 'p': True}, expected_marked={'u': False, 'p': True})
        # The method is expected to update both the profile and the user
        # if the email address is the same for both.
        Profile.all_objects.filter(pk=self.profile.pk).update(email=email)
        self.mark_emails_as_invalid_tests(
            email, [email],
            expected_updated={'u': True, 'p': True}, expected_marked={'u': True, 'p': True})
        # Providing a parameter of an email erroneously marked as invalid
        # is not expected to add one more prefix.
        self.mark_emails_as_invalid_tests(
            email, [invalid_email],
            expected_updated={'u': True, 'p': True}, expected_marked={'u': False, 'p': False})

        # Note: At this point, the profile's email and the account's email
        # are the same, and both are marked as invalid.

        # The `mark_valid_emails` method invoked with no parameters
        # is not expected to change anything.
        self.mark_emails_as_valid_tests(
            email, None,
            expected_updated=False, expected_unmarked=False)
        # The method invoked with an empty list
        # is not expected to change anything.
        self.mark_emails_as_valid_tests(
            email, [],
            expected_updated=False, expected_unmarked=False)
        # The method invoked with a non-existing email parameter
        # is not expected to change anything.
        self.mark_emails_as_valid_tests(
            email, ["a@b.co", f"{settings.INVALID_PREFIX}d.e@f-g.h.ij.km"],
            expected_updated=False, expected_unmarked=False)
        # The method invoked with the existing (clean) email parameter
        # is not expected to change anything, since an email value
        # marked as invalid is anticipated.
        self.mark_emails_as_valid_tests(
            email, [email],
            expected_updated=False, expected_unmarked=False)
        # The method is expected to remove the marker prefix from both
        # the profile and user emails, if these are the same.
        self.mark_emails_as_valid_tests(
            email, [invalid_email],
            expected_updated={'u': True, 'p': True}, expected_unmarked={'u': True, 'p': True})
        # Repeating the operation is not expected to change anything.
        self.mark_emails_as_valid_tests(
            email, [invalid_email, email],
            expected_updated={'u': True, 'p': True}, expected_unmarked={'u': False, 'p': False})
        # The method is expected to update only the corresponding object
        # if email addresses differ for the profile and the user.
        User.objects.filter(pk=self.profile.user.pk).update(
            email=invalid_email
        )
        Profile.all_objects.filter(pk=self.profile.pk).update(
            email=f"{settings.INVALID_PREFIX}nop_qr@s-t-u.vw.xyz"
        )
        self.mark_emails_as_valid_tests(
            email, [f"{settings.INVALID_PREFIX}nop_qr@s-t-u.vw.xyz"],
            expected_updated={'u': False, 'p': True}, expected_unmarked={'u': False, 'p': True})
        self.mark_emails_as_valid_tests(
            email, [invalid_email],
            expected_updated={'u': True, 'p': True}, expected_unmarked={'u': True, 'p': False})

    @override_settings(INVALID_PREFIX='BAD_DATA::')
    def test_mark_identical_emails(self):
        # Having two profiles with the same public email address is
        # permitted. The `mark_invalid_emails` and `mark_valid_emails`
        # methods are expected to update both profile objects.
        profile_two = ProfileSansAccountFactory(with_email=True)
        Profile.all_objects.filter(pk=self.profile.pk).update(email=profile_two.email)
        email = profile_two.email
        invalid_email = f'{settings.INVALID_PREFIX}{email}'

        result = Profile.mark_invalid_emails([email])
        self.profile.refresh_from_db()
        profile_two.refresh_from_db()
        self.assertEqual(self.profile.email, profile_two.email)
        self.assertTrue(self.profile.email.startswith(settings.INVALID_PREFIX))
        self.assertEqual(result[Profile], 2)
        # When one of the profiles has its email already marked as
        # invalid, only the other one is expected to be updated.
        Profile.all_objects.filter(pk=self.profile.pk).update(email=email)
        result = Profile.mark_invalid_emails([email])
        self.profile.refresh_from_db()
        profile_two.refresh_from_db()
        self.assertTrue(self.profile.email.startswith(settings.INVALID_PREFIX))
        self.assertEqual(self.profile.email.count(settings.INVALID_PREFIX), 1)
        self.assertTrue(profile_two.email.startswith(settings.INVALID_PREFIX))
        self.assertEqual(profile_two.email.count(settings.INVALID_PREFIX), 1)
        self.assertEqual(result[Profile], 1)
        # Repeating the operation is not expected to update anything.
        result = Profile.mark_invalid_emails([email])
        self.assertEqual(result[Profile], 0)

        # Both profile objects' emails are expected to have the
        # marker prefix removed.
        result = Profile.mark_valid_emails([invalid_email])
        self.profile.refresh_from_db()
        profile_two.refresh_from_db()
        self.assertEqual(self.profile.email, profile_two.email)
        self.assertEqual(self.profile.email.count(settings.INVALID_PREFIX), 0)
        self.assertEqual(result[Profile], 2)
        # When one of the profiles has its email already marked as
        # valid, only the other one is expected to be updated.
        Profile.all_objects.filter(pk=self.profile.pk).update(email=invalid_email)
        result = Profile.mark_valid_emails([invalid_email])
        self.profile.refresh_from_db()
        profile_two.refresh_from_db()
        self.assertEqual(self.profile.email.count(settings.INVALID_PREFIX), 0)
        self.assertEqual(profile_two.email.count(settings.INVALID_PREFIX), 0)
        self.assertEqual(result[Profile], 1)
        # Repeating the operation is not expected to update anything.
        result = Profile.mark_valid_emails([email])
        self.assertEqual(result[Profile], 0)


@tag('integration')
class FamilyMemberModelIntegrationTests(TestCase):
    """
    Tests for customizations of the FamilyMember proxy model.
    """

    @classmethod
    def setUpTestData(cls):
        cls.profile_only_tenant = ProfileSansAccountFactory()
        cls.profile_with_account = ProfileFactory()
        cls.place_owner = ProfileFactory()
        cls.place = PlaceFactory(owner=cls.place_owner)

    def test_owner_setting_on_incorrect_model(self):
        # Setting the `owner` on a `Profile` instance is expected to fail.
        with self.assertRaises(AttributeError):
            self.profile_only_tenant.owner = -5
        self.assertIs(self.profile_only_tenant.owner, self.profile_only_tenant)
        with self.assertRaises(AttributeError):
            self.profile_only_tenant.owner = self.place_owner
        self.assertIs(self.profile_only_tenant.owner, self.profile_only_tenant)

    def test_owner_setting_with_invalid_value(self):
        # Setting the `owner` on a `FamilyMember` instance is expected to
        # fail if the value is of incorrect type.
        profile_only_tenant = FamilyMember.all_objects.get(pk=self.profile_only_tenant.pk)
        with self.assertRaises(ValueError):
            profile_only_tenant.owner = -6
        with self.assertRaises(ValueError):
            profile_only_tenant.owner = self.place

    def test_owner_setting(self):
        # Setting the `owner` on a `FamilyMember` instance without a user
        # account is expected to succeed.
        profile_only_tenant = FamilyMember.all_objects.get(pk=self.profile_only_tenant.pk)
        profile_only_tenant.owner = self.place_owner
        self.assertIsInstance(profile_only_tenant.owner, Profile)
        self.assertEqual(profile_only_tenant.owner.pk, self.place_owner.pk)
        # Setting the `owner` on a `FamilyMember` instance with a user
        # account is expected to succeed but do nothing.
        profile_with_account = FamilyMember.all_objects.get(pk=self.profile_with_account.pk)
        profile_with_account.owner = self.place_owner
        self.assertIsInstance(profile_with_account.owner, Profile)
        self.assertEqual(profile_with_account.owner.pk, self.profile_with_account.pk)

    def test_default_owner(self):
        # The default `owner` of a family member without a user account is
        # expected to be None.
        profile_only_tenant = FamilyMember.all_objects.get(pk=self.profile_only_tenant.pk)
        self.assertIsNone(profile_only_tenant.owner, None)
        # The default `owner` of a family member with a user account is
        # expected to be the family member themselves.
        profile_with_account = FamilyMember.all_objects.get(pk=self.profile_with_account.pk)
        self.assertIsInstance(profile_with_account.owner, Profile)
        self.assertEqual(profile_with_account.owner.pk, self.profile_with_account.pk)


@tag('integration')
class PlaceModelIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = CountryRegionFactory()
        cls.place = PlaceFactory(country=cls.region.country, state_province=cls.region.iso_code)

        cls.place.family_members.add(ProfileSansAccountFactory(
            birth_date=Faker('date_between', start_date=date(1976, 1, 2), end_date=date(1976, 12, 30)),
        ))
        cls.place.family_members.add(ProfileSansAccountFactory(
            first_name="", last_name="",
            birth_date=None,
        ))
        cls.place.family_members.add(ProfileSansAccountFactory(
            first_name="", last_name="",
            birth_date=Faker('date_between', start_date=date(1963, 1, 2), end_date=date(1963, 12, 30)),
        ))
        cls.place.family_members.add(ProfileSansAccountFactory(
            birth_date=Faker('date_between', start_date=date(1975, 1, 2), end_date=date(1975, 12, 30)),
            deleted_on=timezone.now(),
        ))
        cls.place.conditions.add(ConditionFactory())
        cls.place.conditions.add(ConditionFactory())
        cls.place.conditions.add(ConditionFactory())

        cls.other_account = UserFactory(profile__first_name="", profile__last_name="")
        cls.deleted_account = UserFactory(profile__deleted_on=timezone.now())
        cls.place.authorized_users.add(cls.other_account)
        cls.place.authorized_users.add(cls.deleted_account)

    def test_rawdisplay(self):
        with self.subTest(raw_display='family members'):
            family = self.place.family_members.order_by('pk')
            self.assertEqual(
                self.place.rawdisplay_family_members(),
                f"{str(family[2])} (1963), {str(family[3])} (1975), "
                f"{str(family[0])} (1976), {str(family[1])} (?)"
            )

        with self.subTest(raw_display='conditions'):
            conditions = self.place.conditions.order_by('pk')
            self.assertEqual(
                self.place.rawdisplay_conditions(),
                f"{str(conditions[0])}, {str(conditions[1])}, {str(conditions[2])}"
            )

    def test_family_members_cache(self):
        # The cache is expected to contain all family members,
        # ordered by their birth date.
        family = [p.pk for p in self.place.family_members.order_by('birth_date')]
        transform = lambda p: p.pk
        with self.assertNumQueries(1):
            cache = self.place.family_members_cache()
            self.assertQuerysetEqual(cache, family, transform, ordered=True)
        with self.assertNumQueries(0):
            cache = self.place.family_members_cache()
            self.assertQuerysetEqual(cache, family, transform, ordered=True)

        # When the family members are already prefetched, the
        # cache is expected to contain these objects.
        nuclear_family = [family[1], family[3]]
        family_members = Prefetch(
            'family_members',
            Profile.all_objects.filter(pk__in=nuclear_family).select_related(None))
        place = Place.all_objects.prefetch_related(family_members).get(pk=self.place.pk)
        with self.assertNumQueries(0):
            cache = place.family_members_cache()
            self.assertQuerysetEqual(cache, nuclear_family, transform, ordered=False)

    def test_family_is_anonymous(self):
        # When a place does not have any family members, the expected result is False.
        place = PlaceFactory(owner=self.place.owner)
        self.assertFalse(place.family_is_anonymous)

        profile_with_account = self.other_account.profile
        profile_only_tenant = self.place.family_members.order_by('pk')

        # When a place has multiple family members, the expected result is False.
        place = Place.all_objects.get(pk=place.pk)
        place.family_members.add(profile_only_tenant[1], profile_only_tenant[2])
        self.assertFalse(place.family_is_anonymous)
        place = Place.all_objects.get(pk=place.pk)
        place.family_members.add(profile_with_account)
        self.assertFalse(place.family_is_anonymous)

        # When a place has a single family member with an account, the expected
        # result is False.
        place = Place.all_objects.get(pk=place.pk)
        place.family_members.set({profile_with_account})
        self.assertFalse(place.family_is_anonymous)

        # When a place has a single family member without an account but whose
        # names are given, the expected result is False.
        place = Place.all_objects.get(pk=place.pk)
        place.family_members.set({profile_only_tenant[3]})
        self.assertFalse(place.family_is_anonymous)

        # When a place has a single family member without an account whose names
        # are not given, the expected result is True.
        place = Place.all_objects.get(pk=place.pk)
        place.family_members.set({profile_only_tenant[2]})
        self.assertTrue(place.family_is_anonymous)

    def test_authorized_users_cache(self):
        # The cache is expected to contain the users authorized to access the
        # full details of the place, according to the method parameters.
        test_data = [
            ({'complete': False, 'also_deleted': False}, {self.other_account.pk}),
            ({'complete': True, 'also_deleted': False}, {self.other_account.pk}),
            ({'complete': False, 'also_deleted': True}, {self.other_account.pk, self.deleted_account.pk}),
            ({'complete': True, 'also_deleted': True}, {self.other_account.pk, self.deleted_account.pk}),
        ]
        for params, expected_set in test_data:
            for attempt, expected_queries in {"first": 1, "second": 0}.items():
                with self.subTest(**params, attempt=attempt):
                    with self.assertNumQueries(expected_queries):
                        cache = self.place.authorized_users_cache(**params)
                        self.assertQuerysetEqual(cache, expected_set, lambda u: u.pk, ordered=False)
                        if params['complete'] and not params['also_deleted']:
                            # Accessing the profile of the authorized user is not expected
                            # to result in an additional database query.
                            self.assertEqual(cache[0].profile.pk, self.other_account.profile.pk)

    def test_conditions_cache(self):
        # The cache is expected to contain all hosting conditions defined for the place.
        conditions = [c.pk for c in self.place.conditions.order_by('pk')]
        with self.assertNumQueries(1):
            cache = self.place.conditions_cache()
            self.assertQuerysetEqual(cache, conditions, lambda c: c.pk, ordered=False)
        with self.assertNumQueries(0):
            cache = self.place.conditions_cache()
            self.assertQuerysetEqual(cache, conditions, lambda c: c.pk, ordered=False)

    @tag('subregions')
    def test_subregion(self):
        # An existing subregion object's type is expected to be CountryRegion
        # and its `iso_code` is expected to equal the `state_province` value
        # of the place.
        subregion = self.place.subregion
        self.assertIsInstance(subregion, CountryRegion)
        self.assertEqual(subregion.pk, self.region.pk)
        self.assertEqual(subregion.iso_code, self.place.state_province)
        # Saving the object is expected to be disabled.
        current_name = subregion.latin_name
        subregion.latin_name = "SUBSTITUTE"
        subregion.save()
        subregion.refresh_from_db()
        self.assertEqual(subregion.latin_name, current_name)

        # Modifying the `state_province` field of the place is expected to
        # result in a new subregion object.
        # This object's type is expected to be CountryRegion.
        # SIDE EFFECT: self.place.state_province is altered but not saved
        #              to the database; this shouldn't affect other tests.
        faker = Faker._get_faker(locale='zh-CN')
        self.place.state_province = faker.word()
        subregion, old_subregion = self.place.subregion, subregion
        self.assertIsNot(subregion, old_subregion)
        self.assertIsInstance(subregion, CountryRegion)
        self.assertNotEqual(subregion.pk, old_subregion.pk)

        # A non-existing subregion object's `latin_code` is expected to equal
        # the `state_province` value of the place.
        self.assertNotEqual(subregion.pk, self.region.pk)
        self.assertEqual(subregion.latin_code, self.place.state_province)
        # Saving the object is expected to be disabled.
        self.assertIsNone(subregion.pk)
        subregion.save()
        self.assertIsNone(subregion.pk)
