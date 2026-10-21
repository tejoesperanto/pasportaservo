from typing import cast

from django.contrib.auth.models import Group
from django.test import override_settings, tag
from django.urls import reverse_lazy

from django_webtest import WebTest

from hosting.models import PasportaServoUser
from tests import DjangoWebtestResponse, UserTag
from tests.factories import (
    AdminUserFactory, PlaceFactory,
    ProfileFactory, StaffUserFactory, UserFactory,
)


@tag('views', 'views-book')
@override_settings(ROOT_URLCONF='book.tests.urls')
class BookContactExportViewTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse_lazy('contact_export')
        cls.admin = AdminUserFactory.create(profile=None)
        cls.supervisor = UserFactory.create(profile=None)
        Group.objects.get_or_create(name='AQ')[0].user_set.add(cls.supervisor)

    def test_access(self):
        test_users: dict[UserTag, PasportaServoUser | None] = {
            UserTag('anonymous'): None,
            UserTag('regular'): UserFactory.create(profile=None),
            UserTag('staff'): StaffUserFactory.create(profile=None),
            UserTag('supervisor'): self.supervisor,
            UserTag('superuser'): self.admin,
        }
        for user_tag, user in test_users.items():
            with self.subTest(user=user_tag):
                response = self.app.get(self.url, user=user, status='*')
                if user is None:
                    # Unauthenticated users are expected to be
                    # redirected to the login page.
                    self.assertEqual(response.status_code, 302)
                elif 'superuser' in user_tag:
                    # The admin user is expected to be granted
                    # access to the endpoint.
                    self.assertEqual(response.status_code, 200)
                else:
                    # All other users, including supervisors and
                    # staff, are expected to be denied access.
                    self.assertEqual(response.status_code, 404)

    def test_output(self):
        INCLUDED, EXCLUDED = "Included place", "Excluded place"
        owner = ProfileFactory.create()
        # Available, not deleted places are expected to be included in the CSV.
        PlaceFactory.create_batch(
            2, owner=owner, available=True,
            short_description=INCLUDED)
        # Available, not deleted places that are configured to be shown on the
        # website are expected to be included in the CSV.
        PlaceFactory.create(
            owner=owner, available=True,
            visibility_value={'online_public': True, 'in_book': False},
            short_description=f"{INCLUDED}; (visible online)")
        # Available, not deleted places that are configured to be printed in
        # the book are expected to be included in the CSV.
        PlaceFactory.create(
            owner=owner, available=True,
            visibility_value={'online_public': False, 'in_book': True},
            short_description=f"{INCLUDED}; (visible in book)")
        # Available but deleted places are expected to be excluded from the CSV.
        PlaceFactory.create(
            owner=owner, available=True, deleted=True,
            short_description=f"{EXCLUDED}; deleted")
        # Available places that are configured to be hidden on the website and
        # not printed in the book, are expected to be excluded from the CSV.
        PlaceFactory.create(
            owner=owner, available=True,
            visibility_value={'online_public': False, 'in_book': False},
            short_description=f"{EXCLUDED}; hidden")
        # Unavailable places, even those whose owner is willing to meet with
        # visitors, are expected to be excluded from the CSV.
        PlaceFactory.create(
            owner=owner, available=False,
            short_description=f"{EXCLUDED}; unavailable")
        PlaceFactory.create(
            owner=owner, available=False, have_a_drink=True,
            short_description=f"{EXCLUDED}; unavailable")
        PlaceFactory.create(
            owner=owner, available=False, tour_guide=True,
            short_description=f"{EXCLUDED}; unavailable")
        # Places with deceased owners are expected to be excluded from the CSV.
        PlaceFactory.create(
            owner__deceased=True, available=True,
            short_description=f"{EXCLUDED}; deceased owner")
        # Places whose owners have invalid email addresses are expected to be
        # excluded from the CSV.
        PlaceFactory.create(
            owner__user__invalid_email=True, available=True,
            short_description=f"{EXCLUDED}; invalid email")

        response = cast(DjangoWebtestResponse, self.app.get(self.url, user=self.admin))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv')
        self.assertContains(response, INCLUDED, count=4)
        self.assertNotContains(response, EXCLUDED)
