from random import randint
from unittest import skipUnless

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.test import RequestFactory, TestCase, override_settings, tag
from django.urls import reverse
from django.views.generic import CreateView, View

from anymail.exceptions import AnymailAPIError, AnymailRecipientsRefused
from anymail.message import AnymailMessage
from django_webtest import WebTest

from core.auth import AuthMixin, AuthRole
from hosting.models import Preferences, VisibilitySettings

from ..assertions import AdditionalAsserts
from ..factories import (
    AdminUserFactory, PhoneFactory, PlaceFactory,
    ProfileFactory, ProfileSansAccountFactory, UserFactory,
)


@tag('integration', 'mailing')
class MailingTests(AdditionalAsserts, TestCase):
    """
    Tests for the mailing functionalities and integration with an external
    provider.
    """

    @tag('external')
    @override_settings(**settings.TEST_EMAIL_BACKENDS['live'])
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
