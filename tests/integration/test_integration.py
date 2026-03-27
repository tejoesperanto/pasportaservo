import json
import sys
import time
import uuid
from random import randint
from typing import Optional, TypedDict
from unittest import skipUnless

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.test import (
    LiveServerTestCase, RequestFactory, TestCase, override_settings, tag,
)
from django.urls import NoReverseMatch, reverse
from django.views.generic import CreateView, View

from anymail.exceptions import (
    AnymailAPIError, AnymailInsecureWebhookWarning, AnymailRecipientsRefused,
)
from anymail.message import AnymailMessage
from anymail.signals import AnymailTrackingEvent, EventType as AnymailEventType
from anymail.webhooks.base import AnymailBaseWebhookView
from django_webtest import WebTest

from core.auth import AuthMixin, AuthRole
from core.hooks import process_suppression
from hosting.models import (
    PasportaServoUser, Preferences, TrackingModel, VisibilitySettings,
)
from tests import DjangoWebtestResponse

from ..assertions import AdditionalAsserts
from ..factories import (
    AdminUserFactory, PhoneFactory, PlaceFactory,
    ProfileFactory, ProfileSansAccountFactory, UserFactory,
)


@tag('integration', 'mailing')
class MailingTests(AdditionalAsserts, WebTest):
    """
    Tests for the mailing functionalities and integration with an external
    provider.
    """

    @tag('external')
    @override_settings(**settings.TEST_EMAIL_BACKENDS['remote-test'])
    @skipUnless(settings.TEST_EXTERNAL_SERVICES, 'External services are tested only explicitly')
    def test_mail_backend_integration_contract(self):
        message = AnymailMessage(
            "Single message test",
            to=["abcd@example.org"],
            body="Fusce felis lectus, dapibus ut velit non, pharetra molestie tellus.")
        with self.assertNotRaises(AnymailAPIError):
            message.send()
        status = message.anymail_status
        self.assertEqual(status.status, {'sent'})
        self.assertIsNotNone(status.message_id)
        self.assertEqual(list(status.recipients.keys()), ["abcd@example.org"])

        message = AnymailMessage(
            "Broadcast message test",
            to=["efgh@example.org"],
            body="Mauris purus sapien, aliquam id viverra ut, bibendum sed metus.")
        message.esp_extra = {'MessageStream': 'broadcast'}
        with self.assertNotRaises(AnymailAPIError):
            message.send()
        status = message.anymail_status
        self.assertEqual(status.status, {'sent'})
        self.assertIsNotNone(status.message_id)
        self.assertEqual(list(status.recipients.keys()), ["efgh@example.org"])

        message = AnymailMessage(
            "Invalid recipient test",
            to=["pqrs@localhost"],
            body="Curabitur elit massa, elementum id consectetur at, semper a odio.")
        with self.assertRaises(AnymailRecipientsRefused):
            message.send()
        status = message.anymail_status
        self.assertEqual(status.status, {'invalid'})
        self.assertIsNone(status.message_id)

    @staticmethod
    def _email_for_user(user: PasportaServoUser) -> str:
        return (
            user._meta.model.objects
            .filter(pk=user.pk)
            .values_list('email', flat=True)
            .get()
        )

    def test_mail_tracking_signal(self):
        """
        Direct tests of the signal receiver for tracking webhook call.
        """
        users = {
            'basic': UserFactory.create(profile=None),
            'basic_invalid_email': UserFactory.create(profile=None, invalid_email=True),
            'regular': UserFactory.create(),
            'regular_invalid_email': UserFactory.create(invalid_email=True),
        }
        initial_emails = {user_tag: users[user_tag].email for user_tag in users}

        def restore_emails():
            for user_tag in users:
                users[user_tag].email = initial_emails[user_tag]
            PasportaServoUser.objects.bulk_update(users.values(), ['email'])

        # Unmonitored events are expected to cause no change in the database.
        ignored_event_types = [
            AnymailEventType.QUEUED, AnymailEventType.SENT,
            AnymailEventType.UNKNOWN, AnymailEventType.FAILED,
        ]
        for ignored_event in ignored_event_types:
            with self.subTest(expected_ignored=ignored_event):
                event = AnymailTrackingEvent(event_type=ignored_event)
                for user, expected_email in zip(users.values(), initial_emails.values()):
                    event.recipient = user._clean_email
                    with self.assertNotRaises(Exception):
                        process_suppression(AnymailBaseWebhookView, event, 'dummy')
                    # The email address of the related user is expected to
                    # remain as-is.
                    self.assertEqual(self._email_for_user(user), expected_email)
            restore_emails()

        # Monitored events due to deliveries originating in a different
        # environment are expected to be dropped and cause no change in
        # the database.
        processed_event_types = [
            AnymailEventType.BOUNCED, AnymailEventType.REJECTED,
            AnymailEventType.COMPLAINED,
        ]
        for processed_event in processed_event_types:
            with self.subTest(expected_processed=processed_event):
                event = AnymailTrackingEvent(
                    event_type=processed_event, metadata={'env': 'NOT_REAL_ENVIRONMENT'})
                for user, expected_email in zip(users.values(), initial_emails.values()):
                    event.recipient = user._clean_email
                    with self.assertNotRaises(Exception):
                        process_suppression(AnymailBaseWebhookView, event, 'dummy')
                    # The email address of the related user is expected to
                    # remain as-is.
                    self.assertEqual(self._email_for_user(user), expected_email)
            restore_emails()

        # Monitored events affecting the current environment are expected
        # to result in the email addresses of the affected users being marked
        # as invalid.
        for processed_event in processed_event_types:
            with self.subTest(expected_processed=processed_event):
                event = AnymailTrackingEvent(event_type=processed_event)
                for user in users.values():
                    event.recipient = user._clean_email
                    with self.assertNotRaises(Exception):
                        process_suppression(AnymailBaseWebhookView, event, 'dummy')
                    # The email address of the related user is expected to be
                    # marked invalid.
                    expected_email = f'{settings.INVALID_PREFIX}{user._clean_email}'
                    self.assertEqual(self._email_for_user(user), expected_email)
            restore_emails()

    def test_mail_tracking_webhook(self):
        user = UserFactory.create(profile=None)
        response: DjangoWebtestResponse

        # Verify that the webhook exists at the expected URL (status of
        # 405 Method Not Allowed and not 404 Not Found).
        with self.assertWarns(AnymailInsecureWebhookWarning):
            response = self.app.get('/mail_hook/tracking/', status='*')
        self.assertEqual(response.status_code, 405,
                         msg="Expected 'Method Not Allowed' due to use of GET")

        # Verify that the webhook's processing view is set up correctly.
        with self.assertNotRaises(NoReverseMatch):
            webhook_url = reverse('postmark_tracking_webhook')

        # Verify that the webhook call is rejected when the authentication
        # secret is not provided.
        with self.settings(ANYMAIL_WEBHOOK_SECRET='abcdef:123456'):
            response = self.app.post(
                webhook_url, '{}', content_type='application/json', status='*')
        self.assertEqual(response.status_code, 400,
                         msg="Expected 'Bad Request' due to missing auth secret")

        # A properly configured call for a delivery event is expected to
        # be accepted by the webhook but not processed, with the user's
        # email address remaining as previously.
        for test_user in (None, user):
            with self.subTest(
                    event_type='delivery',
                    user='existing' if test_user else 'non-existing',
            ):
                test_delivery_payload = {
                    "MessageID": "883953f4-6105-42a2-a16a-77a8eac79483",
                    "MessageStream": "outbound",
                    "RecordType": "Delivery",
                    "Recipient": user._clean_email if test_user else "Not.Real-D@ps.org",
                    "DeliveredAt": "2026-03-01T22:33:44.087208Z",
                }
                with self.settings(ANYMAIL_WEBHOOK_SECRET='qwerty:789456'):
                    self.app.authorization = ('Basic', ('qwerty', '789456'))
                    response = self.app.post(
                        webhook_url,
                        json.dumps(test_delivery_payload),
                        content_type='application/json',
                        status='*',
                    )
                self.assertEqual(response.status_code, 200,
                                 msg="Expected successful Delivery webhook call")
                self.assertEqual(self._email_for_user(user), user._clean_email)

        # A properly configured call for a bounce event is expected to
        # be accepted and processed by the webhook. If the event relates
        # to an existing user, that user's email address is expected to
        # be marked as invalid.
        for test_user in (None, user):
            with self.subTest(
                    event_type='bounce',
                    user='existing' if test_user else 'non-existing',
            ):
                test_bounce_payload = {
                    "MessageID": "883953f4-6105-42a2-a16a-77a8eac79483",
                    "MessageStream": "outbound",
                    "RecordType": "Bounce",
                    "Type": "SoftBounce",
                    "Inactive": True,
                    "Email": user._clean_email if test_user else "Not.Real-B@ps.org",
                    "BouncedAt": "2026-03-03T21:32:43.087208Z",
                }
                with self.settings(ANYMAIL_WEBHOOK_SECRET='qwerty:24680'):
                    self.app.authorization = ('Basic', ('qwerty', '24680'))
                    response = self.app.post(
                        webhook_url,
                        json.dumps(test_bounce_payload),
                        content_type='application/json',
                        status='*',
                    )
                self.assertEqual(response.status_code, 200,
                                 msg="Expected successful Bounce webhook call")
                if test_user is None:
                    # A bounce event for a non-existing recipient is not expected to
                    # result in a change of the user's email address.
                    self.assertEqual(self._email_for_user(user), user._clean_email)
                else:
                    # A bounce event for an existing recipient (user) is expected to
                    # cause that user's email address being marked invalid.
                    self.assertEqual(
                        self._email_for_user(user),
                        '{}{}'.format(settings.INVALID_PREFIX, user._clean_email)
                    )


@tag('integration', 'mailing')
class MailingWebhookTests(AdditionalAsserts, LiveServerTestCase):
    """
    Tests for integration with an external email service provider (ESP).
    """
    port = 8006

    class WebhookTimeout(AssertionError):
        pass

    @staticmethod
    def _wait_for_user_email_change(user: PasportaServoUser, initial_email: str):
        start = time.time()
        timeout = 95  # seconds
        expected_email = '{}{}'.format(settings.INVALID_PREFIX, initial_email)
        CLEAR_LINE_ESCAPE_CODE = "\033[2K\r"

        sys.stdout.write("\nStarting polling.")
        sys.stdout.flush()
        while True:
            if MailingTests._email_for_user(user) == expected_email:
                sys.stdout.write(CLEAR_LINE_ESCAPE_CODE)
                sys.stdout.flush()
                return
            if (elapsed := time.time() - start) > timeout:
                sys.stdout.write(CLEAR_LINE_ESCAPE_CODE)
                sys.stdout.flush()
                raise MailingWebhookTests.WebhookTimeout(
                    f"User's email not marked as invalid after {timeout} seconds")
            sys.stdout.write(
                f"{CLEAR_LINE_ESCAPE_CODE}Awaiting webhook invocation"
                f" targeting {initial_email} for {int(elapsed)} seconds...")
            sys.stdout.flush()
            time.sleep(5)

    @tag('external')
    @override_settings(**settings.TEST_EMAIL_BACKENDS['remote-live'])
    @skipUnless(settings.TEST_EXTERNAL_SERVICES, 'External services are tested only explicitly')
    def test_mail_tracking_webhook_integration_contract(self):
        # This test cannot be run without externalizing the local web server.
        # Via Serveo:
        # 1. Generate an SSH key pair using `ssh-keygen`.
        # 2. Add the public key to Serveo's web console: https://console.serveo.net/ssh/keys.
        # 3. Run `ssh -R ps-egress:80:127.0.0.1:8006 serveo.net` in terminal.
        # 4. POSTMARK_SERVER_TOKEN should point to the Sandbox server for
        #    which the webhook is defined.
        # The test polls twice for 90 seconds, but it is still flaky because
        # Postmark might send the bounce event even after 2 minutes.

        class UserDef(TypedDict):
            user_id: uuid.UUID
            actual_email: str
            dispatch_email: str
            user: PasportaServoUser
        test_data: dict[str, UserDef] = {}
        for email_tag in ('non-existing', 'existing'):
            user_id = uuid.uuid4()
            test_data[email_tag] = {}  # type: ignore
            test_data[email_tag]['user_id'] = user_id
            test_data[email_tag]['actual_email'] = (
                f'{user_id.hex.upper()}@bounce-testing.postmarkapp.com'
            )
            test_data[email_tag]['dispatch_email'] = (
                test_data[email_tag]['actual_email'] if email_tag == 'existing'
                else test_data[email_tag]['actual_email'].lower()
            )
            test_data[email_tag]['user'] = UserFactory.create(
                profile=None, email=test_data[email_tag]['actual_email'],
            )

        for email_tag in test_data:
            with self.subTest(email=email_tag):
                message = EmailMessage(
                    f"bounce test for {test_data[email_tag]['user_id']} ({email_tag})",
                    "---",
                    to=[test_data[email_tag]['dispatch_email']],
                    headers={'X-PM-Bounce-Type': 'HardBounce'})
                with self.assertNotRaises(AnymailAPIError):
                    message.send()
                assertion = (
                    self.assertNotRaises if email_tag == 'existing' else self.assertRaises
                )
                with assertion(self.WebhookTimeout):
                    self._wait_for_user_email_change(
                        test_data[email_tag]['user'],
                        test_data[email_tag]['actual_email']
                    )


@tag('integration')
class ModelSignalTests(AdditionalAsserts, TestCase):
    """
    Tests for automated management of visibility and preferences objects
    linked to their respective parent objects, via the Django pre-save,
    post-save, and post-delete signals.
    """

    def test_visibility_signals(self):
        profile = ProfileFactory.build()
        self.object_linkage_tests(profile, 'email_visibility', 'PublicEmail', save_related='user')

        phone = PhoneFactory.build(profile=profile)
        self.object_linkage_tests(phone, 'visibility', 'Phone')

        place = PlaceFactory.build(owner=profile)
        self.object_linkage_tests(place, 'visibility', 'Place')

        place2 = PlaceFactory.build(owner=profile)
        self.object_linkage_tests(place2, 'family_members_visibility', 'FamilyMembers')

        profile_only_tenant = ProfileSansAccountFactory.build()
        self.object_linkage_tests(profile_only_tenant, 'email_visibility', 'PublicEmail')

        data = serializers.serialize('json', [profile, phone, place])

        self.object_codeletion_tests(profile_only_tenant, 1)
        self.object_codeletion_tests(place2, 2)
        self.object_codeletion_tests(place, 2)
        self.object_codeletion_tests(phone, 1)
        self.object_codeletion_tests(profile, 1)

        # When loading data from fixtures, the pre-save and post-save signals
        # are expected to be a no-op. Meaning, no new visibility objects are
        # expected to be created in the database.
        number_existing_vis_objects = VisibilitySettings.objects.count()
        deserialized_objects = []
        for obj in serializers.deserialize('json', data):
            deserialized_objects.append((obj.object._meta.model, obj.object.pk))
            obj.save()
        self.assertEqual(VisibilitySettings.objects.count(), number_existing_vis_objects)

        # Clean up the database to avoid violations of constraints.
        for model, object_pk in reversed(deserialized_objects):
            model.all_objects.filter(pk=object_pk).delete()

    def test_preferences_signals_full_profile(self):
        profile_with_account = ProfileFactory.build()
        number_entities = Preferences.objects.count()

        # Upon saving a new profile object, a preferences object is expected
        # to be automatically created in the database and linked to the
        # profile.
        self.assertIsNone(profile_with_account.pk)
        self.assertRaises(AttributeError, lambda: profile_with_account.pref)
        profile_with_account.user.save()
        profile_with_account.user_id = profile_with_account.user.pk
        profile_with_account.save()
        self.assertIsNotNone(profile_with_account.pk)
        self.assertNotRaises(AttributeError, lambda: profile_with_account.pref)
        self.assertEqual(profile_with_account.pref.profile_id, profile_with_account.pk)
        self.assertEqual(Preferences.objects.count(), number_entities + 1)

        # Upon saving an existing profile object, no new preferences object
        # is expected to be created.
        profile_with_account.save()
        profile_with_account.refresh_from_db()
        self.assertEqual(Preferences.objects.count(), number_entities + 1)

        data = serializers.serialize(
            'json',
            [profile_with_account, profile_with_account.pref])
        profile_pk = profile_with_account.pk
        pref_pk = profile_with_account.pref.pk

        # Upon deleting a profile object, the deletion is expected to
        # cascade and the preferences object linked to the profile is
        # expected to be automatically removed in the database.
        profile_with_account.delete()
        self.assertEqual(Preferences.objects.count(), number_entities)

        # When loading data from fixtures, the pre-save and post-save
        # signals are expected to be a no-op. Meaning, a new preferences
        # object is not expected to be created; rather, the previously
        # linked one is expected to be restored.
        for obj in serializers.deserialize('json', data):
            obj.save()
        self.assertEqual(Preferences.objects.count(), number_entities + 1)
        pref_obj = Preferences.objects.filter(profile_id=profile_pk)
        self.assertEqual(len(pref_obj), 1)
        self.assertEqual(pref_obj[0].pk, pref_pk)
        # Clean up the database to avoid violations of constraints.
        profile_with_account._meta.model.all_objects.filter(pk=profile_pk).delete()

    def test_preferences_signals_limited_profile(self):
        profile_only_tenant = ProfileSansAccountFactory.build()
        number_entities = Preferences.objects.count()

        # Upon saving a new object of a limited profile without an account,
        # no preferences objects are expected to be created and attempting
        # to access the preferences of such profile is expected to raise an
        # AttributeError exception.
        self.assertIsNone(profile_only_tenant.pk)
        self.assertRaises(AttributeError, lambda: profile_only_tenant.pref)
        profile_only_tenant.save()
        self.assertIsNotNone(profile_only_tenant.pk)
        self.assertRaises(AttributeError, lambda: profile_only_tenant.pref)
        self.assertEqual(Preferences.objects.count(), number_entities)

        # Upon saving an existing limited profile object, no other change
        # in the database is expected.
        profile_only_tenant.save()
        profile_only_tenant.refresh_from_db()
        self.assertEqual(Preferences.objects.count(), number_entities)

        # Upon deleting a limited profile object, no other change in the
        # database is expected.
        profile_only_tenant.delete()
        self.assertEqual(Preferences.objects.count(), number_entities)

    def object_linkage_tests(self, object, linked_visibility_type, object_type, save_related=None):
        self.assertIsNone(object.pk)
        self.assertIsNone(getattr(object, f'{linked_visibility_type}_id'))
        if save_related:
            getattr(object, save_related).save()
            setattr(object, f'{save_related}_id', getattr(object, save_related).pk)
        object.save()

        # Upon saving, a visibility object is expected to be automatically
        # created in the database with default values (per parent object's
        # type and the visibility type) and linked to the parent object.
        self.assertIsNotNone(object.pk)
        self.assertIsNotNone(getattr(object, f'{linked_visibility_type}_id'))
        attr = getattr(object, linked_visibility_type)
        attr.refresh_from_db()
        self.assertEqual(attr.model_id, object.pk)
        self.assertEqual(attr.model_type, object_type)

        # Upon saving a second time, no new visibility object is expected
        # to be created.
        attr_id = attr.pk
        number_existing_vis_objects = VisibilitySettings.objects.count()
        object.save()
        object.refresh_from_db()
        self.assertEqual(getattr(object, f'{linked_visibility_type}_id'), attr_id)
        self.assertEqual(VisibilitySettings.objects.count(), number_existing_vis_objects)

    def object_codeletion_tests(self, object, count_linked_visibility_objects):
        # Upon deletion, the visibility objects linked to the parent object
        # are expected to be automatically removed in the database.
        self.assertIsNotNone(object.pk)
        number_existing_vis_objects = VisibilitySettings.objects.count()
        object.delete()
        self.assertEqual(
            VisibilitySettings.objects.count(),
            number_existing_vis_objects - count_linked_visibility_objects
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
        cls.admin = AdminUserFactory.create(profile=None)
        cls.supervisor = UserFactory.create(profile=None)
        cls.country_group.user_set.add(cls.supervisor)

        cls.profile = ProfileFactory.create(locale='fi')
        cls.place = PlaceFactory.create(
            country='NL', closest_city='Enschede',
            owner=cls.profile)

    def object_update_tests(
            self,
            object: TrackingModel, page_url: str, form_id: str,
            privileged_user: PasportaServoUser,
            owner_user: Optional[PasportaServoUser] = None,
            partial_update: bool = False,
    ):
        # Update of an object (profile, place, phone) by an
        # administrator or supervisor is expected to mark it
        # as checked.
        page = self.app.get(page_url, user=privileged_user)
        self.assertIn(form_id, page.forms)
        response = page.forms[form_id].submit()
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
        self.assertIn(form_id, page.forms)
        response = page.forms[form_id].submit()
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
        self.object_update_tests(
            self.profile, profile_form_url, 'id_profile_form', self.admin,
        )

    def test_place_update(self):
        place_form_url = reverse('place_update', kwargs={'pk': self.place.pk})

        self.assertIsNone(self.place.checked_on)
        self.assertIsNone(self.place.checked_by)
        self.object_update_tests(
            self.place, place_form_url, 'id_place_form', self.supervisor,
        )

    def test_place_location_update(self):
        place_location_form_url = reverse(
            'place_location_update',
            kwargs={'pk': self.place.pk})

        self.assertIsNone(self.place.checked_on)
        self.assertIsNone(self.place.checked_by)
        self.object_update_tests(
            self.place, place_location_form_url, 'id_place_location_form',
            self.supervisor, partial_update=True,
        )

    def test_family_member_update(self):
        family_member = ProfileSansAccountFactory.create(locale='et')
        self.place.family_members.add(family_member)
        family_member_form_url = reverse(
            'family_member_update',
            kwargs={'pk': family_member.pk, 'place_pk': self.place.pk})

        self.assertIsNone(family_member.checked_on)
        self.assertIsNone(family_member.checked_by)
        self.object_update_tests(
            family_member, family_member_form_url, 'id_family_member_form',
            self.supervisor, owner_user=self.place.owner.user,
        )

    def test_phone_update(self):
        phone = PhoneFactory.create(profile=self.profile)
        phone_form_url = reverse(
            'phone_update',
            kwargs={'pk': phone.pk, 'profile_pk': self.profile.pk})

        self.assertIsNone(phone.checked_on)
        self.assertIsNone(phone.checked_by)
        self.object_update_tests(
            phone, phone_form_url, 'id_phone_form', self.admin,
        )


@tag('integration', 'auth')
class AuthRoleTests(TestCase):
    """
    Tests for correct implementation of the Authorization Role enum.
    """

    @classmethod
    def setUpTestData(cls):
        cls.root_roles = [role for role in AuthRole if role.parent is None]
        cls.child_roles = [role for role in AuthRole if role.parent]

    def test_str(self):
        for role in AuthRole:
            with self.subTest(role=repr(role)):
                if not role.parent:
                    self.assertEqual(str(role), role.name)
                else:
                    self.assertEqual(str(role), f"{role.parent.name} ({role.name})")

    def test_repr(self):
        for role in AuthRole:
            with self.subTest(role=repr(role)):
                if not role.parent:
                    self.assertEqual(repr(role), f"<AuthRole.{role.name}: {role.value}>")
                else:
                    self.assertEqual(
                        repr(role),
                        f"<AuthRole.{role.name} :: AuthRole.{role.parent.name}>"
                    )

    def test_equal(self):
        # Sanity check.
        for role in self.root_roles + self.child_roles:
            with self.subTest(role=repr(role)):
                self.assertTrue(role == role)
                # Comparison to literals is expected to be unsupported.
                self.assertFalse(role == role.value)
        # Child roles are expected to compare equal to their parent roles.
        for role in self.child_roles:
            with self.subTest(role=repr(role)):
                self.assertTrue(role == role.parent)
                self.assertTrue(role.parent == role)
        # Child roles are expected to be uncomparable between themselves.
        for role in self.child_roles:
            with self.subTest(role=repr(role)):
                for another_role in set(self.child_roles) - {role}:
                    with self.assertRaises(NotImplementedError):
                        role == another_role

    def test_not_equal(self):
        # Sanity check.
        for role in self.root_roles:
            with self.subTest(role=repr(role)):
                for another_role in set(self.root_roles) - {role}:
                    self.assertTrue(role != another_role)
        # Child roles are expected to compare unequal to other non-child
        # roles except for their own parent role.
        for role in self.child_roles:
            with self.subTest(role=repr(role)):
                for another_role in set(self.root_roles) - {role.parent}:
                    self.assertTrue(role != another_role)
                    self.assertTrue(another_role != role)
        # Child roles are expected to be uncomparable between themselves.
        for role in self.child_roles:
            with self.subTest(role=repr(role)):
                for another_role in set(self.child_roles) - {role}:
                    with self.assertRaises(NotImplementedError):
                        role != another_role

    def test_comparison_root_role(self):
        # Root roles are expected to be comparable between them according
        # to increasing order.
        role_index = randint(1, len(self.root_roles) - 1)
        role = self.root_roles[role_index]
        for i in range(len(self.root_roles)):
            another_role = self.root_roles[i]
            with self.subTest(role=repr(role), another_role=repr(another_role)):
                if i < role_index:
                    self.assertTrue(role > another_role)
                    self.assertTrue(another_role < role)
                    # Comparison to literals is expected to be unsupported.
                    self.assertRaises(
                        TypeError,
                        lambda literal=another_role.value: role > literal)
                elif i == role_index:
                    self.assertTrue(role >= another_role)
                    self.assertFalse(role > another_role)
                    self.assertTrue(another_role <= role)
                    self.assertFalse(another_role < role)
                    # Comparison to literals is expected to be unsupported.
                    self.assertRaises(
                        TypeError,
                        lambda literal=another_role.value: role >= literal)
                else:
                    self.assertTrue(role < another_role)
                    self.assertTrue(another_role > role)
                    # Comparison to literals is expected to be unsupported.
                    self.assertRaises(
                        TypeError,
                        lambda literal=another_role.value: role < literal)

    def test_comparison_child_role(self):
        role_index = randint(1, len(self.child_roles) - 1)
        role = self.child_roles[role_index]
        parent_role_index = self.root_roles.index(role.parent)

        # Child roles are expected to be comparable to the root roles,
        # according to the position of their parent role.
        for i in range(len(self.root_roles)):
            another_role = self.root_roles[i]
            with self.subTest(role=repr(role), another_role=repr(another_role)):
                if i < parent_role_index:
                    self.assertTrue(role > another_role)
                    # Comparison to literals is expected to be unsupported.
                    self.assertRaises(
                        TypeError,
                        lambda literal=another_role.value: role > literal)
                    self.assertFalse(role <= another_role)
                elif i == parent_role_index:
                    self.assertTrue(role >= another_role)
                    self.assertFalse(role > another_role)
                    # Comparison to literals is expected to be unsupported.
                    self.assertRaises(
                        TypeError,
                        lambda literal=another_role.value: role >= literal)
                else:
                    self.assertTrue(role < another_role)
                    self.assertFalse(role >= another_role)
                    # Comparison to literals is expected to be unsupported.
                    self.assertRaises(
                        TypeError,
                        lambda literal=another_role.value: role < literal)

        # Child roles are expected to be uncomparable between themselves.
        for another_role in self.child_roles:
            with self.subTest(role=repr(role), another_role=repr(another_role)):
                with self.assertRaises(NotImplementedError):
                    role > another_role
                with self.assertRaises(NotImplementedError):
                    role >= another_role
                with self.assertRaises(NotImplementedError):
                    role < another_role
                with self.assertRaises(NotImplementedError):
                    role <= another_role


@tag('integration', 'auth')
class AuthMixinConfigTests(AdditionalAsserts, TestCase):
    """
    Tests for correct configuration of the AuthMixin on views (incorrect
    setup shall alert the developer during execution).
    """

    def test_missing_auth_check(self):
        class MyTestView(AuthMixin, View):
            minimum_role = AuthRole.VISITOR

            def get(self, request, *args, **kwargs):
                return JsonResponse({})

        class MyAnonymousTestView(AuthMixin, View):
            allow_anonymous = True

            def get(self, request, *args, **kwargs):
                return JsonResponse({})

        request = RequestFactory().get('/look-up')
        expected_message = (
            "AuthMixin is present on the view {} but no authorization check was performed."
        )

        # Accessing a misconfigured view as a logged in user is expected to result in
        # a warning and no authorization check is expected to be performed.
        request.user = UserFactory(profile=None)  # Simulate a logged-in user.
        with self.assertWarnsMessage(
                AuthMixin.MisconfigurationWarning, expected_message.format('MyTestView')):
            response = MyTestView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        # Accessing a misconfigured view for which anonymous access is allowed, as a
        # non-authenticated user, is expected to result in a warning.
        request.user = AnonymousUser()  # Simulate a non-authenticated user.
        with self.assertWarnsMessage(
                AuthMixin.MisconfigurationWarning, expected_message.format('MyAnonymousTestView')):
            response = MyAnonymousTestView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_missing_auth_base(self):
        class MyBadCreateTestView(AuthMixin, CreateView):
            pass

        class MyBadAnonymousCreateTestView(AuthMixin, CreateView):
            allow_anonymous = True

        class MyGoodCreateTestView(AuthMixin, CreateView):
            minimum_role = AuthRole.VISITOR
            allow_anonymous = True

            def dispatch(self, request, *args, **kwargs):
                kwargs['auth_base'] = None
                return super().dispatch(request, *args, **kwargs)

            def get(self, request, *args, **kwargs):
                return JsonResponse({})

        request = RequestFactory().get('/look-up')
        expected_message = (
            "Creation base not found. Make sure {}'s auth_base is accessible by AuthMixin "
            "as a dispatch kwarg."
        )

        request.user = UserFactory(profile=None)  # Simulate a logged-in user.
        # Accessing a misconfigured view (which does not define an authorization base)
        # as a logged in user is expected to result in an exception.
        with self.assertRaisesMessage(
                ImproperlyConfigured, expected_message.format('MyBadCreateTestView')):
            MyBadCreateTestView.as_view()(request)
        # Accessing (via GET) a properly configured view as a logged in user is not
        # expected to raise an exception. The view is expected to have the user's role
        # (in this case, a VISITOR).
        view = MyGoodCreateTestView()
        view.setup(request)
        with self.assertNotRaises(ImproperlyConfigured):
            response = view.dispatch(request)
        self.assertTrue(hasattr(view, 'role'))
        self.assertEqual(view.role, AuthRole.VISITOR)
        self.assertEqual(response.status_code, 200)

        request.user = AnonymousUser()  # Simulate a non-authenticated user.
        # Accessing a misconfigured view (which does not define an authorization base)
        # for which anonymous access is allowed, with a non-authenticated user, is
        # expected to result in an exception.
        with self.assertRaisesMessage(
                ImproperlyConfigured, expected_message.format('MyBadAnonymousCreateTestView')):
            MyBadAnonymousCreateTestView.as_view()(request)
        # Accessing a misconfigured view for which anonymous access is NOT allowed,
        # with a non-authenticated user, is not expected to raise an exception, since
        # authentication check ought to preceed the authorization check.
        # The view is expected to have the user's role and redirect the user to the
        # authentication page.
        view = MyBadCreateTestView()
        view.setup(request)
        with self.assertNotRaises(ImproperlyConfigured):
            response = view.dispatch(request)
        self.assertTrue(hasattr(view, 'role'))
        self.assertEqual(view.role, AuthRole.VISITOR)
        expected_url = '{}?{}=/look-up'.format(reverse('login'), settings.REDIRECT_FIELD_NAME)
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)
        # Accessing (via GET) a properly configured view for which anonymous access is
        # allowed, as a non-authenticated user, is not expected to raise an exception.
        view = MyGoodCreateTestView()
        view.setup(request)
        with self.assertNotRaises(ImproperlyConfigured):
            response = view.dispatch(request)
        self.assertTrue(hasattr(view, 'role'))
        self.assertEqual(view.role, AuthRole.VISITOR)
        self.assertEqual(response.status_code, 200)
