from django.contrib.auth.models import Group
from django.test import tag
from django.urls import reverse

from django_webtest import WebTest

from ..factories import (
    AdminUserFactory, PhoneFactory, PlaceFactory,
    ProfileFactory, ProfileSansAccountFactory, UserFactory,
)


@tag('integration')
class CheckStatusTests(WebTest):
    """
    Tests for the `checked_on` and `checked_by` flags being updated on
    the models after a corresponding form on the website is saved.
    """

    @classmethod
    def setUpTestData(cls):
        cls.country_group = Group.objects.get_or_create(name='NL')[0]
        cls.admin = AdminUserFactory(profile=None)
        cls.supervisor = UserFactory(profile=None)
        cls.country_group.user_set.add(cls.supervisor)

        cls.profile = ProfileFactory(locale='fi')
        cls.place = PlaceFactory(
            country='NL', closest_city='Enschede',
            owner=cls.profile)

    def object_update_tests(
            self, object, page_url, privileged_user, owner_user=None, partial_update=False):
        # Update of an object (profile, place, phone) by an
        # administrator or supervisor is expected to mark it
        # as checked.
        page = self.app.get(page_url, user=privileged_user)
        response = page.form.submit()
        self.assertEqual(response.status_code, 302, msg=response)
        object.refresh_from_db()
        if not partial_update:
            self.assertIsNotNone(object.checked_on)
            self.assertEqual(object.checked_by, privileged_user)
        else:
            self.assertIsNone(object.checked_on)
            self.assertIsNone(object.checked_by)

        # Update of an object (profile, place, phone) by the
        # user who the object belongs to is expected to unmark
        # it as checked.
        if not owner_user:
            owner_user = object.owner.user
        page = self.app.get(page_url, user=owner_user)
        response = page.form.submit()
        self.assertEqual(response.status_code, 302, msg=response)
        object.refresh_from_db()
        self.assertIsNone(object.checked_on)
        self.assertIsNone(object.checked_by)

    def test_profile_update(self):
        profile_form_url = reverse(
            'profile_update',
            kwargs={'pk': self.profile.pk, 'slug': self.profile.autoslug})

        self.assertIsNone(self.profile.checked_on)
        self.assertIsNone(self.profile.checked_by)
        self.object_update_tests(self.profile, profile_form_url, self.admin)

    def test_place_update(self):
        place_form_url = reverse('place_update', kwargs={'pk': self.place.pk})

        self.assertIsNone(self.place.checked_on)
        self.assertIsNone(self.place.checked_by)
        self.object_update_tests(self.place, place_form_url, self.supervisor)

    def test_place_location_update(self):
        place_location_form_url = reverse(
            'place_location_update',
            kwargs={'pk': self.place.pk})

        self.assertIsNone(self.place.checked_on)
        self.assertIsNone(self.place.checked_by)
        self.object_update_tests(
            self.place, place_location_form_url, self.supervisor,
            partial_update=True)

    def test_family_member_update(self):
        family_member = ProfileSansAccountFactory(locale='et')
        self.place.family_members.add(family_member)
        family_member_form_url = reverse(
            'family_member_update',
            kwargs={'pk': family_member.pk, 'place_pk': self.place.pk})

        self.assertIsNone(family_member.checked_on)
        self.assertIsNone(family_member.checked_by)
        self.object_update_tests(
            family_member, family_member_form_url, self.supervisor,
            owner_user=self.place.owner.user)

    def test_phone_update(self):
        phone = PhoneFactory(profile=self.profile)
        phone_form_url = reverse(
            'phone_update',
            kwargs={'pk': phone.pk, 'profile_pk': self.profile.pk})

        self.assertIsNone(phone.checked_on)
        self.assertIsNone(phone.checked_by)
        self.object_update_tests(phone, phone_form_url, self.admin)
