from django.test import TestCase, tag

from hosting.models import FamilyMember, Profile

from ..factories import PlaceFactory, ProfileFactory, ProfileSansAccountFactory


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
