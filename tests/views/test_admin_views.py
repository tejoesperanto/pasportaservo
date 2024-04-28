from datetime import datetime, timedelta
from typing import Callable, Iterable, Optional
from urllib.parse import urlencode

from django.contrib.auth.models import Group
from django.core import mail
from django.test import override_settings, tag
from django.utils.timezone import make_aware

from factory import Faker

from hosting.models import PasportaServoUser

from .. import with_type_hint
from ..factories import StaffUserFactory, UserFactory
from .mixins import FormViewTestsMixin
from .pages import MassMailPage, MassMailResultPage
from .testcasebase import BasicViewTests


class AdministratorUserSetupMixin(with_type_hint(BasicViewTests)):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.regular_users = cls.users.copy()
        cls.privileged_users = {
            'supervisor': UserFactory(profile=None),
            'staff': StaffUserFactory(profile=None),
        }
        Group.objects.get_or_create(name='AQ')[0].user_set.add(
            cls.privileged_users['supervisor']
        )

        cls.user = UserFactory.create(is_superuser=True)
        cls.users = {
            'admin': cls.user,
        }

    def test_access(self):
        # The view is expected to be accessible only by the administrators
        # and no other user (including supervisors).
        tested_users = self.regular_users | self.privileged_users
        for user_tag in tested_users:
            with self.subTest(user=user_tag):
                page = self.view_page.open(self, user=tested_users[user_tag], status='*')
                self.assertEqual(page.response.status_code, 404)
        with self.subTest(user='admin'):
            page = self.view_page.open(self, user=self.user, status='*')
            self.assertEqual(page.response.status_code, 200)


@tag('views', 'views-admin')
class MassMailViewTests(AdministratorUserSetupMixin, FormViewTestsMixin, BasicViewTests):
    view_page = MassMailPage

    def test_submit_invalid_values(self):
        # Invalid or missing values are expected to result in form errors
        # and no email being dispatched.
        expected_errors = {
            'en': {
                'subject': "This field is required.",
                'preheader': "This field is required.",
                'heading': "This field is required.",
                'body': "This field is required.",
                'categories': "Select a valid choice."
                              + " 1qaz2wsx is not one of the available choices.",
                'test_email': "Enter a valid email address.",
            },
            'eo': {
                'subject': "Ĉi tiu kampo estas deviga.",
                'preheader': "Ĉi tiu kampo estas deviga.",
                'heading': "Ĉi tiu kampo estas deviga.",
                'body': "Ĉi tiu kampo estas deviga.",
                'categories': "Elektu validan elekton."
                              + " 1qaz2wsx ne estas el la eblaj elektoj.",
                'test_email': "Enigu retadreson en ĝusta formo.",
            },
        }
        for lang in expected_errors:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self, user=self.user)
                page.submit({
                    'massmail-categories': "1qaz2wsx",
                    'massmail-test_email': "ppqqrrtt",
                })
                # Unsuccessful submission is expected to return the user
                # to the same page, not redirect to the results page.
                self.assertEqual(page.response.status_code, 200)
                self.assertLength(mail.outbox, 0)
                for field in expected_errors[lang]:
                    with self.subTest(field=field):
                        # Verify context.
                        self.assertFormError(
                            page.response, 'form', field,
                            expected_errors[lang][field]
                        )
                        # Verify actual output.
                        self.assertEqual(
                            page.get_form_errors(f'massmail-{field}'),
                            [expected_errors[lang][field]]
                        )

    def _build_test_dataset(self):
        faker = Faker._get_faker()
        cutoff_date = make_aware(datetime(2014, 11, 24))
        generated_users = {}

        very_long_ago = (
            lambda:
                faker.date_time_between(start_date=cutoff_date + timedelta(days=1), end_date='-5y')
        )
        generated_users['old_system'] = {
            True: [
                # User who logged in before PS.3 was launched.
                UserFactory(last_login=make_aware(faker.date_time(end_datetime=cutoff_date))),
                # User who logged in on the date of launching.
                UserFactory(last_login=cutoff_date),
                # User with an available place, who logged in prior to launch date.
                UserFactory(
                    last_login=make_aware(faker.date_time(end_datetime=cutoff_date)),
                    places=1, places__available=True, places__in_book=True),
            ],
            'FalseHere': [
                # User who logged in after the launch date.
                UserFactory(last_login=make_aware(very_long_ago())),
            ],
            False: [
                # User who never logged in.
                self.regular_users['regular'],
                self.regular_users['basic'],
                # User with an available place, who never logged in (e.g., added manually).
                UserFactory(
                    last_login=None,
                    places=1, places__available=True, places__in_book=True),
                # Deleted user who logged in on the date of launching.
                UserFactory(last_login=cutoff_date, is_active=False),
                # Deceased user who logged in on the date of launching.
                UserFactory(last_login=cutoff_date, deceased_user=True),
                # User with deleted profile, who never logged in.
                UserFactory(last_login=None, deleted_profile=True),
                # User with deleted profile and an available place,
                # who logged in prior to launch date.
                UserFactory(
                    last_login=make_aware(faker.date_time(end_datetime=cutoff_date)),
                    deleted_profile=True,
                    places=[{'available': True, 'in_book': True, 'deleted': True}]),
                # User without profile who logged in prior to launch date.
                UserFactory(
                    last_login=make_aware(faker.date_time(end_datetime=cutoff_date)),
                    profile=None),
                # User without profile who logged in on the date of launching.
                UserFactory(last_login=cutoff_date, profile=None),
            ],
        }

        some_time_ago = lambda: faker.date_time_between(start_date='-725d', end_date='-370d')
        generated_users['users_active_1y'] = {
            True: [
                # User with profile (not a host).
                UserFactory(last_login=make_aware(faker.date_time_this_year())),
                # User with profile and no available place (not a host).
                UserFactory(
                    last_login=make_aware(faker.date_time_this_month()),
                    places=1, places__available=False, places__in_book=False, places__deleted=True),
                # User with profile and an available place.
                UserFactory(
                    last_login=make_aware(faker.date_time_this_month()),
                    places=1, places__available=True, places__in_book=False),
                # User with profile and previously available places (deleted).
                UserFactory(
                    last_login=make_aware(faker.date_time_this_month()),
                    places=[{'in_book': False}, {'in_book': True}],
                    places__available=True, places__deleted=True),
                # The administrator.
                self.user,
            ],
            'FalseHere': [
                # User with profile (not a host), who has not recently logged in.
                UserFactory(last_login=make_aware(some_time_ago())),
                # User with profile and an available place, who has not recently logged in.
                UserFactory(
                    last_login=make_aware(some_time_ago()),
                    places=1, places__available=True, places__in_book=False),
                # User with profile and an unavailable place, who has not recently logged in.
                UserFactory(
                    last_login=make_aware(some_time_ago()),
                    places=1, places__available=False, places__in_book=False),
            ],
            False: [
                # User who never logged in.
                self.regular_users['regular'],
                # Deleted user with profile.
                UserFactory(last_login=make_aware(faker.date_time_this_year()), is_active=False),
                # Deceased user with profile.
                UserFactory(last_login=make_aware(faker.date_time_this_year()), deceased_user=True),
                # User with deleted profile.
                UserFactory(last_login=make_aware(faker.date_time_this_year()), deleted_profile=True),
                # User without profile.
                UserFactory(last_login=make_aware(faker.date_time_this_month()), profile=None),
            ],
        }

        long_ago = lambda: faker.date_time_between(start_date='-5y', end_date='-735d')
        generated_users['users_active_2y'] = {
            True: [
                # Users who logged in in the last 2 years.
                *generated_users['users_active_1y']['FalseHere'],
                # Also users who logged in in the last year.
                *generated_users['users_active_1y'][True],
            ],
            'FalseHere': [
                # User with profile (not a host), who has not recently logged in.
                UserFactory(last_login=make_aware(long_ago())),
                # User with profile and an available place, who has not recently logged in.
                UserFactory(
                    last_login=make_aware(long_ago()),
                    places=1, places__available=True, places__in_book=False),
                # User with profile and an unavailable place, who has not recently logged in.
                UserFactory(
                    last_login=make_aware(long_ago()),
                    places=1, places__available=False, places__in_book=False),
            ],
            False: [
                # Users who never logged in, or logged in recently but are no longer active.
                *generated_users['users_active_1y'][False],
                # User with profile and a deleted place (available in the past),
                # who has not recently logged in.
                UserFactory(
                    last_login=make_aware(long_ago()),
                    places=[{'available': True, 'in_book': False, 'deleted': True}]),
            ],
        }

        generated_users['not_hosts'] = {
            # Not hosts: all users previously defined as True and FalseHere,
            # who do not own or did not own an available place.
            True:
                self._filter_generated_users(
                    generated_users,
                    condition=lambda user: (
                        not any(place.available for place in user.profile.owned_places.all())
                    ),
                ),
            False:
                self._filter_generated_users(generated_users, which_subkeys=False),
        }

        generated_users['in_book'] = {
            True: [
                # User with at least one publishable available place,
                # who logged in after the launch date.
                UserFactory(
                    last_login=make_aware(very_long_ago()),
                    places=[
                        {'available': True, 'in_book': True},
                        {'available': True, 'in_book': True, 'deleted': True},
                        {'available': True, 'in_book': False, 'deleted': True},
                    ]),
                # User with at least one publishable available place,
                # who logged in after the launch date.
                UserFactory(
                    last_login=make_aware(very_long_ago()),
                    places=[
                        {'available': False, 'in_book': False},
                        {'available': True, 'in_book': False},
                        {'available': True, 'in_book': True},
                        {'available': True, 'in_book': False, 'deleted': True},
                    ]),
            ],
            'FalseHere': [
                # User with no currently publishable available places,
                # who logged in after the launch date.
                UserFactory(
                    last_login=make_aware(long_ago()),
                    places=[
                        {'available': True, 'in_book': False},
                        {'available': True, 'in_book': True, 'deleted': True},
                    ]),
            ],
            False: [
                # User with a previously available place (deleted),
                # who logged in after the launch date.
                UserFactory(
                    last_login=make_aware(very_long_ago()),
                    places=[{'available': True, 'in_book': True, 'deleted': True}]),
                # User with a deleted profile and an available place,
                # who logged in after the launch date.
                UserFactory(
                    last_login=make_aware(some_time_ago()),
                    deleted_profile=True,
                    places=1, places__available=True, places__in_book=True),
                # + Previously generated users who are either deleted, deceased, have no profile,
                # have a deleted profile, logged in prior to the launch date, never logged in,
                # have no (presently) available places, or have no (presently) publishable places.
            ],
        }

        def not_in_book_condition(user: PasportaServoUser):
            available_places = user.profile.owned_places.filter(deleted=False, available=True)
            return (
                len(available_places) > 0
                and all(not place.in_book for place in available_places)
            )
        generated_users['not_in_book'] = {
            True: (
                self._filter_generated_users(
                    generated_users, ['users_active_2y', 'old_system', 'in_book'],
                    condition=not_in_book_condition,
                )
            ),
            False: [
                # Previously generated users who do not fulfil the conditions:
                # Active user who logged in after the launch date, with a non-deleted profile,
                # having all of their currently available (not deleted) places marked as not
                # for publishing in the booklet.
            ],
        }

        return generated_users

    def _filter_generated_users(
            self,
            generated_users: dict[str, dict[str, Iterable[PasportaServoUser]]],
            keys: Optional[Iterable[str]] = None,
            which_subkeys: bool = True,
            condition: Callable[[PasportaServoUser], bool] = lambda user: True,
    ) -> Iterable[PasportaServoUser]:
        keys = keys or generated_users.keys()
        return set(
            user
            for key in keys
            for selection, userset in generated_users[key].items()
            for user in userset
            if (selection if which_subkeys else selection is False)
            if condition(user)
        )

    def test_submit(self):
        # A properly constructed message (where all form fields are valid) is
        # expected to result in dispatching of individual emails to each user
        # within the selected category, with the content provided in the form
        # and customized per user.

        test_users = self._build_test_dataset()
        # from pprint import pprint; pprint(test_users)

        for lang in ['en', 'eo']:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                faker = Faker._get_faker('la' if lang == 'eo' else lang)
                test_data = {
                    'subject': faker.sentence(),
                    'preheader': "{nomo}: " + faker.sentence(),
                    'heading': faker.word().capitalize() * 2,
                    'body': "Important email *{}* for all, {{nomo}}.",
                    'categories': None,
                    'test_email': f"Zamenhof.{faker.email().capitalize()}",
                }
                test_data['body'] = test_data['body'].format(test_data['heading'])
                test_users['test'] = {True: [
                    UserFactory(
                        email=test_data['test_email'],
                        profile__first_name=test_data['test_email'],
                    )
                ]}

                for category in test_users:
                    with self.subTest(category=category):
                        page = self.view_page.open(self, user=self.user)
                        self.user.refresh_from_db()
                        mail.outbox = []
                        page.submit({
                            f'massmail-{key}': (value if key != 'categories' else category)
                            for key, value in test_data.items()
                        })
                        # Successful submission is expected to result in a
                        # redirect to the results page.
                        self.assertEqual(page.response.status_code, 302)
                        self.assertEqual(
                            page.response.location,
                            f'{MassMailResultPage.url}?' + urlencode({
                                'nb': len(test_users[category][True]),
                            })
                        )
                        # The number of emails dispatched is expected to be
                        # equal to the number of users within the category.
                        self.assertLength(mail.outbox, len(test_users[category][True]))
                        for mailitem in mail.outbox:
                            # The content of each individual email is expected
                            # to correspond to the values of the form and include
                            # the name of the user.
                            self.assertEqual(mailitem.subject, test_data['subject'])
                            recipient = [
                                u for u in test_users[category][True] if [u.email] == mailitem.to
                            ]
                            self.assertLength(recipient, 1)
                            recipient_name = recipient[0].profile.first_name
                            self.assertEqual(
                                mailitem.body,
                                test_data['body'].format(nomo=recipient_name)
                            )
                            self.assertLength(getattr(mailitem, 'alternatives', []), 1)
                            mailitem_htmlbody = mailitem.alternatives[0][0]
                            self.assertIn(f"<em>{test_data['heading']}</em>", mailitem_htmlbody)
                            self.assertEqual(mailitem_htmlbody.count(recipient_name), 2)
                            self.assertIn(
                                test_data['preheader'].format(nomo=recipient_name),
                                mailitem_htmlbody
                            )


@tag('views', 'views-admin')
class MassMailSentViewTests(AdministratorUserSetupMixin, BasicViewTests):
    view_page = MassMailResultPage

    def test_result_output(self):
        # The view is expected to show the result of mass mail submission
        # and the number of messages dispatched according to the value of
        # the `nb` parameter.
        faker = Faker._get_faker()
        test_data = [
            None, '', faker.word(), 0, 1, faker.random_int(min=2),
        ]
        for lang in self.view_page.explicit_url:
            for result in test_data:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(lang=lang, result=result)
                ):
                    if result is not None:
                        result_param = {'nb': result}
                    else:
                        result_param = {}
                    page = self.view_page.open(self, user=self.user, extra_params=result_param)
                    if result == 0:
                        # No emails were sent.
                        self.assertEqual(
                            page.get_heading_text(),
                            self.view_page.page_title_failure[lang]
                        )
                        self.assertEqual(
                            page.get_result_element().text(),
                            {
                                'en': "You sent 0 emails.",
                                'eo': "Vi sendis 0 mesaĝojn.",
                            }[lang]
                        )
                        self.assertFalse(page.get_result_element().has_class("text-success"))
                    else:
                        # A specific number or an unknown number of emails was sent.
                        self.assertEqual(
                            page.get_heading_text(),
                            self.view_page.page_title_success[lang]
                        )
                        expected_count = (
                            result
                            if isinstance(result, int)
                            else {'en': "the", 'eo': "la"}[lang]
                        )
                        expected_plural = (
                            {'en': "s", 'eo': "j"}[lang]
                            if result != 1
                            else ""
                        )
                        self.assertEqual(
                            page.get_result_element().text(),
                            {
                                'en': f"You sent {expected_count} email{expected_plural}. Well done!",
                                'eo': f"Vi sendis {expected_count} mesaĝo{expected_plural}n. Bonege!",
                            }[lang]
                        )
                        self.assertCssClass(page.get_result_element(), "text-success")
