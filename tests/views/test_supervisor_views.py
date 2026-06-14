from collections import namedtuple
from datetime import timedelta
from random import sample
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.http import Http404
from django.test import RequestFactory, override_settings, tag
from django.urls import NoReverseMatch, reverse_lazy
from django.utils.timezone import make_aware

from django_countries.data import COUNTRIES
from django_webtest.backends import WebtestUserBackend
from factory import Faker
from waffle.testutils import override_switch

from hosting.models import TrackingModel
from hosting.views.verification import InfoStaffCheckStatusDisplayView

from .. import DjangoWebtestResponse
from ..factories import (
    AdminUserFactory, PhoneFactory, PlaceFactory,
    ProfileFactory, StaffUserFactory, UserFactory,
)
from .pages.base import PageTemplate
from .testcasebase import ViewAsserts, ViewTestingBase


# Temporary solution until a new version of Django-WebTest is available.
class WebtestUserPassthroughBackend(WebtestUserBackend):
    def has_perm(self, user_obj, perm, obj=None):
        return False


@tag('views', 'views-supervisor')
@override_settings(
    WEBTEST_AUTHENTICATION_BACKEND=(
        'tests.views.test_supervisor_views.WebtestUserPassthroughBackend'
    ),
)
class InfoStaffCheckStatusDisplayViewTests(ViewAsserts, ViewTestingBase):
    class CheckStatusSnippet(PageTemplate):
        view_class = InfoStaffCheckStatusDisplayView
        alternative_urls = {
            'profile': PageTemplate._RequiresReverseURL('staff_profile_check_status', {'pk': 0}),
            'place': PageTemplate._RequiresReverseURL('staff_place_check_status', {'pk': 0}),
            'phone': PageTemplate._RequiresReverseURL('staff_phone_check_status', {'pk': 0}),
        }
        template = 'hosting/snippets/checked.html'
        check_status = {
            'en': {True: "Checked", False: "Not checked"},
            'eo': {True: "Kontrolita", False: "Nekontrolita"},
        }
    snippet_page = CheckStatusSnippet

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.users['supervisor_no_profile'] = UserFactory(profile=None)
        cls.users['supervisor_disabled_profile'] = UserFactory(deleted_profile=True)
        cls.users['supervisor_inactive'] = UserFactory(is_active=False)
        for c in sample(list(COUNTRIES), 2):
            Group.objects.get_or_create(name=c)[0].user_set.add(*(
                cls.users[user_tag] for user_tag in cls.users
                if user_tag.startswith('supervisor')
            ))
        cls.users['staff'] = StaffUserFactory(profile=None)
        cls.users['admin'] = AdminUserFactory(profile=None, is_staff=False)
        cls.users['admin_inactive'] = AdminUserFactory(profile=None, is_active=False)

        cls.allowed_access = ['supervisor', 'admin']
        approval_types = ['no approval', 'approval expired', 'approval valid']
        cls.allowed_categories: dict[str, dict[str, TrackingModel]] = {
            'profile': dict(zip(
                approval_types, [cls.user.profile, *ProfileFactory.create_batch(2)]
            )),
            'place': dict(zip(
                approval_types, PlaceFactory.create_batch(3, owner=cls.user.profile)
            )),
            'phone': dict(zip(
                approval_types, PhoneFactory.create_batch(3, profile=cls.user.profile)
            )),
        }
        faker = Faker._get_faker()
        for category in cls.allowed_categories:
            obj = cls.allowed_categories[category]['approval expired']
            obj.checked_on = make_aware(faker.date_time_between('-2y', '-1y'))
            obj.save(update_fields=['checked_on'])
            obj = cls.allowed_categories[category]['approval valid']
            obj.checked_on = make_aware(faker.date_time_between('-355d', '-5d'))
            obj.save(update_fields=['checked_on'])

    def user_is_expected_access(self, user_tag: str):
        return (
            'inactive' not in user_tag
            and any(user_type in user_tag for user_type in self.allowed_access)
        )

    def test_view_url(self):
        """
        Verifies that the view can be found at the expected URLs.
        """
        self._assert_view_url_alt(
            self.snippet_page, user=self.users['admin'],
            url_kwargs_per_tag={
                category: {'pk': self.allowed_categories[category]['no approval'].pk}
                for category in self.allowed_categories
            })
        # TODO: Variable explicit URLs.

    def test_access(self):
        """
        Tests that the view is accessible only by supervisors and administrators.
        """
        for category in self.allowed_categories:
            for checked_object in self.allowed_categories[category].values():
                url = self.snippet_page.get_complete_url(category, {'pk': checked_object.pk})
                with self.subTest(category=category):
                    self.assertNotRaises(NoReverseMatch, lambda: str(url))
                    for user_tag, user in ({'anonymous': None} | self.users).items():
                        with self.subTest(user=user_tag, url=url):
                            self.app.reset()
                            response: DjangoWebtestResponse = self.app.get(
                                url, user=user, status='*')
                            # Users are expected to be authenticated and posses the
                            # supervisor or administrator authorization.
                            if 'anonymous' in user_tag or 'inactive' in user_tag:
                                self.assertEqual(response.status_code, 302)
                            elif self.user_is_expected_access(user_tag):
                                self.assertEqual(response.status_code, 200)
                            else:
                                self.assertEqual(response.status_code, 404)

    def test_unsupported_category(self):
        """
        Tests that an appropriate exception is raised when an unexpected category is used.
        """
        view = InfoStaffCheckStatusDisplayView.as_view(category='dummy')
        request = RequestFactory().get('/check-status')
        for user_tag, user in self.users.items():
            with self.subTest(user=user_tag):
                request.user = user
                with self.assertRaises(Http404) as cm:
                    view(request)
                self.assertEqual(str(cm.exception), "Model category 'dummy' is not supported.")
        with self.assertRaises(NoReverseMatch):
            self.app.get(reverse_lazy('staff_dummy_check_status', kwargs={'pk': 0}))

    @override_switch('HOSTING_DATA_VERIFICATION_EXPIRY', True)
    @patch('hosting.managers.SiteConfiguration.get_solo')
    def test_valid_hosting_object(self, mock_config: MagicMock):
        """
        Tests that the suitable badge is rendered for existing hosting-related objects
        depending on the approval status (either not approved by a supervisor, approved,
        or approved too long ago).
        """
        mock_config.return_value = (
            namedtuple('DummyConfig', 'confirmation_validity_period')(timedelta(days=360))
        )

        for category in self.allowed_categories:
            for approval_type, checked_object in self.allowed_categories[category].items():
                url = self.snippet_page.get_complete_url(category, {'pk': checked_object.pk})
                for user_tag, user in self.users.items():
                    if not self.user_is_expected_access(user_tag):
                        continue
                    for lang in self.snippet_page.check_status:
                        with (
                            override_settings(LANGUAGE_CODE=lang),
                            self.subTest(
                                user=user_tag, lang=lang, category=category, status=approval_type,
                                object=repr(checked_object), checked_on=checked_object.checked_on,
                            )
                        ):
                            response: DjangoWebtestResponse = self.app.get(
                                url, user=user, status='*')
                            self.assertEqual(response.status_code, 200)
                            self.assertTemplateUsed(response, self.snippet_page.template)
                            # The check status badge is expected to be either green or
                            # yellow, and have the text corresponding to the status of
                            # approval by a supervisor.
                            status_element = response.pyquery(".staff")
                            self.assertLength(status_element, 1)
                            if approval_type == 'approval valid':
                                self.assertEqual(
                                    status_element.text(),
                                    self.snippet_page.check_status[lang][True])
                                self.assertCssClass(status_element, "label-success")
                            else:
                                self.assertEqual(
                                    status_element.text(),
                                    self.snippet_page.check_status[lang][False])
                                self.assertCssClass(status_element, "label-warning")

    def test_invalid_hosting_object(self):
        """
        Tests that requesting a badge results in a 404 response for a non-existing object
        (hosting-related) of a supported category.
        """
        for category in self.allowed_categories:
            for checked_object in self.allowed_categories[category].values():
                url = self.snippet_page.get_complete_url(category, {'pk': checked_object.pk + 99})
                for user_tag, user in self.users.items():
                    if not self.user_is_expected_access(user_tag):
                        continue
                    with self.subTest(
                            user=user_tag, category=category, object=repr(checked_object),
                    ):
                        response: DjangoWebtestResponse = self.app.get(url, user=user, status='*')
                        self.assertEqual(response.status_code, 404)
                        self.assertEqual(response.content_type, 'text/html')
                        self.assertTrue('exception' in response.context)
                        self.assertStartsWith(
                            response.context['exception'].lower(),
                            f"no {category} matches the given id")
                        # No check status badge is expected to be rendered and no detailed
                        # error information is expected to be included on the page.
                        self.assertNotContains(
                            response, response.context['exception'], status_code=404)
                        self.assertLength(response.pyquery(".staff"), 0)

                        # The view is expected to support an (empty) JSON response.
                        response = self.app.get(
                            url, user=user, headers={'Accept': 'application/json'}, status='*')
                        self.assertEqual(response.status_code, 404)
                        self.assertEqual(response.content_type, 'application/json')
                        self.assertEqual(response.body, b"")
