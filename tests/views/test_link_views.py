import time
from collections import namedtuple
from typing import Any, Optional, Protocol, TypedDict, cast
from unittest.mock import MagicMock, patch

from django.db.models import Manager
from django.test import override_settings, tag
from django.urls import reverse_lazy
from django.utils.timezone import datetime, make_aware, now, timedelta

from faker import Faker
from itsdangerous import BadSignature, BadTimeSignature, SignatureExpired
from waffle.testutils import override_switch

from hosting.models import TrackingModel
from links.utils import create_unique_url

from .. import DjangoWebtestResponse, with_type_hint
from ..factories import PhoneFactory, PlaceFactory
from .pages import InfoAlreadyConfirmedPage, InfoConfirmedPage, LoginPage
from .pages.links import (
    LinkBadSignaturePage, LinkBadTimeSignaturePage,
    LinkExpiredSignaturePage, LinkInvalidPage,
)
from .testcasebase import (
    BasicViewTests, HeroViewAsserts, ViewAsserts, ViewTestingBase,
)


@tag('views', 'views-links')
class UniqueLinkViewTests(ViewAsserts, HeroViewAsserts, ViewTestingBase):
    @patch('links.views.URLSafeTimedSerializer.loads')
    def test_invalid_token(self, mock_load_token: MagicMock):
        """
        Tests that various types of invalid and no longer valid tokens result in an error response.
        """
        invalid_token_url = reverse_lazy('unique_link', kwargs={'token': 'not-a-legitimate-value'})
        mock_load_token.return_value = {}

        class ResponseDef(TypedDict):
            exception: Exception | None
            page: type[LinkInvalidPage]
        test_dataset: list[ResponseDef] = [
            {
                'exception': SignatureExpired("Signature has expired"),
                'page': LinkExpiredSignaturePage,
            },
            {
                'exception': BadTimeSignature("Bad signature"),
                'page': LinkBadTimeSignaturePage,
            },
            {
                'exception': BadSignature("Bad signature"),
                'page': LinkBadSignaturePage,
            },
            {
                'exception': None,
                'page': LinkInvalidPage,
            },
        ]

        for test_data in test_dataset:
            with self.subTest(expected_page=test_data['page'].__name__):
                mock_load_token.side_effect = test_data['exception']
                test_data['page'].url = invalid_token_url

                for user in [None, self.user]:
                    with self.subTest(user="authenticated" if user else "anonymous"):
                        self._assert_view_url_main(test_data['page'], invalid_token_url, user)
                        self._assert_view_template(test_data['page'], user)
                        self._assert_view_title(test_data['page'], user)

                        for lang in test_data['page'].content_title:
                            with self.subTest(lang=lang):
                                page = test_data['page'].open(self, user=user, reuse_for_lang=lang)
                                # The resulting error page is expected to have 2 headings,
                                # with the title and the details of the problem.
                                heading_elements = page.get_headings()
                                self.assertLength(heading_elements, 2)
                                title_element = heading_elements.eq(0)
                                self.assertEqual(title_element.attr("id"), "title")
                                expected_title = test_data['page'].content_title[lang]
                                self.assertEqual(title_element.text(), expected_title)
                                subtitle_element = heading_elements.eq(1)
                                self.assertEqual(subtitle_element.attr("id"), "subtitle")
                                expected_subtitle = test_data['page'].content_subtitle[lang]['heading']
                                expected_details = test_data['page'].content_subtitle[lang]['details']
                                if expected_details:
                                    self.assertStartsWith(subtitle_element.text(), expected_subtitle)
                                    self.assertEqual(
                                        subtitle_element.find('small').text(),
                                        expected_details)
                                else:
                                    self.assertEqual(subtitle_element.text(), expected_subtitle)
                                # The error page is expected to have no search box.
                                search_element = page.get_hero_content()
                                self.assertLength(search_element, 1)
                                self.assertEqual(cast(str, search_element.html()).strip(), "")

                self._assert_view_header_logged_out(test_data['page'])
                self._assert_view_hero_header_logged_out(test_data['page'])
                self._assert_view_header_logged_in(test_data['page'])
                self._assert_view_hero_header_logged_in(test_data['page'])

    def test_unknown_action(self):
        """
        Tests that a non-defined action results in a server error.
        """
        with self.assertRaises(AttributeError) as cm:
            self.app.get(create_unique_url({'action': 'abracadabra'})[0], expect_errors=True)
        self.assertIn('redirect_abracadabra', str(cm.exception))

    class TrackingObjectData(TypedDict):
        manager: Manager[TrackingModel]
        object: TrackingModel
        confirmation: None | datetime

    class TwoSidedAssertion(Protocol):
        def __call__(self, first: Any, second: Any, msg: Optional[Any] = None) -> None:
            ...

    class TwoSidedABAssertion(Protocol):
        def __call__(self, a: Any, b: Any, msg: Optional[Any] = None) -> None:
            ...

    def object_confirmation_tests(
            self,
            dataset: dict[str, TrackingObjectData],
            listed_objects: list[TrackingModel],
            listed_confirmation_assertion: TwoSidedAssertion | TwoSidedABAssertion,
            unlisted_confirmation_value: None | datetime,
    ):
        for obj_tag in dataset:
            with self.subTest(
                    object=obj_tag, deleted=dataset[obj_tag]['object'] not in listed_objects,
            ):
                # Refresh the `confirmed` attribute by loading via the Manager.
                current_object = dataset[obj_tag]['object'] = dataset[obj_tag]['manager'].get(
                    pk=dataset[obj_tag]['object'].pk
                )
                if current_object not in listed_objects:
                    self.assertEqual(current_object.confirmed_on, unlisted_confirmation_value)
                    self.assertFalse(current_object.confirmed)
                else:
                    self.assertIsNotNone(current_object.confirmed_on)
                    listed_confirmation_assertion(
                        current_object.confirmed_on,
                        dataset[obj_tag]['confirmation'], msg=None)
                    self.assertTrue(current_object.confirmed)
                # Store the new confirmation timestamp.
                dataset[obj_tag]['confirmation'] = current_object.confirmed_on

    @override_switch('HOSTING_DATA_CONFIRMATION_EXPIRY', True)
    @patch('hosting.managers.SiteConfiguration.get_solo')
    def test_confirm_action(self, mock_config: MagicMock):
        """
        Tests that profiles without confirmation or with an expired one can be confirmed
        and double confirmations are accepted but do not update the timestamp. Also tests
        that an appropriate message, acknowledging the action, is displayed to the user.
        """
        mock_config.return_value = namedtuple(
            'DummyConfig', 'confirmation_validity_period, token_max_age, salt'
        )(
            timedelta(weeks=25), 3600, 'test-pepper',
        )
        place_listed = PlaceFactory.create(owner=self.user.profile)
        place_hidden = PlaceFactory.create(owner=self.user.profile)
        place_hidden.visibility.visible_online_public = False
        place_hidden.visibility.save()
        phone_listed = PhoneFactory.create(profile=self.user.profile)
        phone_deleted = PhoneFactory.create(profile=self.user.profile, deleted=True)
        listed_objects: list[TrackingModel] = [
            self.user.profile, place_listed, place_hidden, phone_listed,
        ]
        dataset: dict[str, UniqueLinkViewTests.TrackingObjectData] = {}
        for obj in listed_objects + [phone_deleted]:
            dataset[f'{obj._meta.model.__name__}#{obj.pk}'] = {
                'manager': obj._meta.model.all_objects,
                'object': obj,
                'confirmation': obj.confirmed_on,
            }

        previous_confirmation = make_aware(Faker().date_time_between('-3y', '-1y'))
        url, token = create_unique_url({'action': 'confirm', 'place': place_listed.pk})

        all_unconfirmed: list[bool] = []
        for obj in map(lambda data: data['object'], dataset.values()):
            with self.subTest(object=obj._meta.model.__name__):
                self.assertIsNone(obj.confirmed_on)
                all_unconfirmed.append(True)
        if len(all_unconfirmed) != len(dataset):
            self.assertTrue(False, "Not all objects are unconfirmed")

        # The first confirmation of a previously unconfirmed profile is expected
        # to result in a redirection to a success page and display of a success
        # message.
        response: DjangoWebtestResponse = self.app.get(url)
        self.assertRedirects(
            response, str(InfoConfirmedPage.url), fetch_redirect_response=False)
        self.object_confirmation_tests(
            dataset, listed_objects,
            listed_confirmation_assertion=self.assertNotEqual,
            unlisted_confirmation_value=None)
        page: DjangoWebtestResponse = response.follow()
        self.assertLength(page.context['messages'], 1)
        self.assertStartsWith(
            list(page.context['messages'])[0].message,
            "Bonege, vi konfirmis viajn datenojn.")

        # The second confirmation is expected to result in a redirection to an
        # "already confirmed" page, no success message, and no update of the
        # confirmation timestamp.
        time.sleep(0.100)
        response = self.app.get(url)
        self.assertRedirects(
            response, str(InfoAlreadyConfirmedPage.url), fetch_redirect_response=False)
        self.object_confirmation_tests(
            dataset, listed_objects,
            listed_confirmation_assertion=self.assertEqual,
            unlisted_confirmation_value=None)
        page = response.follow()
        self.assertLength(page.context['messages'], 0)

        # A confirmation of a previously confirmed profile (that was expired) is
        # expected to result in a redirection to a success page with a success
        # message displayed to the user. The confirmation timestamp is expected
        # to be updated to the current time.
        phone_deleted.confirmed_on = previous_confirmation
        phone_deleted.save()
        self.user.profile.confirmed_on = previous_confirmation
        self.user.profile.save()

        time.sleep(0.100)
        response = self.app.get(url)
        self.assertRedirects(
            response, str(InfoConfirmedPage.url), fetch_redirect_response=False)
        self.object_confirmation_tests(
            dataset, listed_objects,
            listed_confirmation_assertion=self.assertGreater,
            unlisted_confirmation_value=previous_confirmation)
        page = response.follow()
        self.assertLength(page.context['messages'], 1)
        self.assertStartsWith(
            list(page.context['messages'])[0].message,
            "Bonege, vi konfirmis viajn datenojn.")

    def test_confirm_action_by_inactive_user(self):
        """
        Tests that a user with a deleted profile or inactive account cannot confirm their profile.
        Tests the same for a user who passed away. Rejection of the action means a generic page
        being shown and no confirmation timestamp being set for the profile or place.
        """
        place = PlaceFactory.create(owner=self.user.profile)
        url, token = create_unique_url({'action': 'confirm', 'place': place.pk})

        # A user who passed away.
        self.assertIsNone(place.confirmed_on)
        self.user.profile.death_date = make_aware(Faker().date_time_between('-3y', '-1y'))
        self.user.profile.save()
        response: DjangoWebtestResponse = self.app.get(url, status='*')
        self.assertEqual(response.status_code, 404,
                         msg=(f"Redirection to {response.location}") if response.location else None)
        place.refresh_from_db()
        self.assertIsNone(place.confirmed_on)

        # A user with a deleted profile.
        self.user.profile.death_date = None
        self.user.profile.deleted_on = now()
        self.user.profile.save()
        response = self.app.get(url, status='*')
        self.assertEqual(response.status_code, 404,
                         msg=(f"Redirection to {response.location}") if response.location else None)
        place.refresh_from_db()
        self.assertIsNone(place.confirmed_on)

        # A user with an inactive account.
        self.user.profile.deleted_on = None
        self.user.profile.save()
        self.user.is_active = False
        self.user.save()
        response = self.app.get(url, status='*')
        self.assertEqual(response.status_code, 404,
                         msg=(f"Redirection to {response.location}") if response.location else None)
        place.refresh_from_db()
        self.assertIsNone(place.confirmed_on)

    def account_email_update_tests(self, email_value: str, verify: Optional[Any] = None):
        update_url, token = create_unique_url(
            {
                'action': 'email_update',
                'pk': self.user.pk,
                'email': email_value,
            } | ({'v': verify} if verify is not None else {})
        )

        self.app.reset()
        # A non-authenticated request is expected to result in a redirection
        # to the login page.
        self.assertNotEqual(self.user.email, email_value)
        response: DjangoWebtestResponse = self.app.get(update_url, status='*')
        self.assertEqual(response.status_code, 302)
        self.assertStartsWith(response.location, str(LoginPage.url))
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.email, email_value)

        # An authenticated request is expected to result in the user account's
        # email being updated and a redirection to the settings page.
        response = self.app.get(update_url, user=self.user, status='*')
        self.assertEqual(response.status_code, 302)
        # TODO: Location == profile settings page.
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, email_value)

    def test_email_update_action(self):
        """
        Tests that the account email is updated to the value indicated within the link
        once the user successfully logs in.
        """
        self.account_email_update_tests("abcd@efg.biz")
        self.account_email_update_tests("hij@kl.mn.info", verify=False)
        self.account_email_update_tests("opq@rs.tu.info", verify=True)


class ConfirmationViewTestsMixin(with_type_hint(ViewTestingBase)):
    view_page: type[InfoConfirmedPage] | type[InfoAlreadyConfirmedPage]

    def test_content(self):
        for lang in self.view_page.content:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self)
                heading_elements = page.get_headings()
                self.assertLength(heading_elements, len(self.view_page.content[lang]))
                expected_content = self.view_page.content[lang].items()
                for i, (heading_level, heading_content) in enumerate(expected_content):
                    with self.subTest(heading=heading_level):
                        element = heading_elements.eq(i)
                        self.assertTrue(element.is_(heading_level),
                                        msg=f"Element's tag name is {element[0].tag}")
                        self.assertCssClass(element, "text-center")
                        self.assertEqual(element.text(), heading_content)
                self.assertLength(page.response.context['messages'], 0)


@tag('views', 'views-links')
class ConfirmedViewTests(ConfirmationViewTestsMixin, BasicViewTests):
    view_page = InfoConfirmedPage


@tag('views', 'views-links')
class AlreadyConfirmedViewTests(ConfirmationViewTestsMixin, BasicViewTests):
    view_page = InfoAlreadyConfirmedPage
