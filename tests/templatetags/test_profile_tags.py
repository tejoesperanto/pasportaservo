import string
from itertools import product
from random import choice, sample
from unittest.mock import patch

from django.contrib.auth import get_backends
from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import FieldDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import CharField, Model, TextChoices
from django.template import Context, Template
from django.test import TestCase, modify_settings, override_settings, tag
from django.utils import timezone
from django.views import generic

from django_countries import countries as all_countries
from django_countries.data import COUNTRIES
from django_countries.fields import Country
from django_webtest import WebTest
from factory import Faker

from hosting.models import Profile

from ..factories import (
    PlaceFactory, ProfileFactory, ProfileSansAccountFactory, UserFactory,
)


@tag('templatetags')
class IsInvalidFilterTests(TestCase):
    template = Template("{% load is_invalid from profile %}{{ value|is_invalid }}")

    @override_settings(INVALID_PREFIX='NULL_')
    def test_invalid_value(self):
        page = self.template.render(Context({'value': "NULL_"}))
        self.assertEqual(page, str(True))
        page = self.template.render(Context({'value': "NULL_void"}))
        self.assertEqual(page, str(True))

        class Nil:
            def __str__(self):
                return "NULL_!"
        page = self.template.render(Context({'value': Nil()}))
        self.assertEqual(page, str(True))

    @override_settings(INVALID_PREFIX='NULL_')
    def test_valid_value(self):
        page = self.template.render(Context({'value': "something"}))
        self.assertEqual(page, str(False))
        page = self.template.render(Context({'value': "null_anything"}))
        self.assertEqual(page, str(False))
        page = self.template.render(Context({'value': "NIL_anything"}))
        self.assertEqual(page, str(False))
        page = self.template.render(Context({'value': "NULLAnything"}))
        self.assertEqual(page, str(False))
        page = self.template.render(Context({'value': "some NULL_ thing"}))
        self.assertEqual(page, str(False))
        page = self.template.render(Context({'value': object()}))
        self.assertEqual(page, str(False))


@tag('templatetags')
class ClearInvalidFilterTests(TestCase):
    template = Template("{% load clear_invalid from profile %}[{{ value|clear_invalid }}]")

    @override_settings(INVALID_PREFIX='$0:')
    def test_filter(self):
        page = self.template.render(Context({'value': ""}))
        self.assertEqual(page, "[]")
        page = self.template.render(Context({'value': "eyB1c2VyOjEgfQ=="}))
        self.assertEqual(page, "[eyB1c2VyOjEgfQ==]")
        page = self.template.render(Context({'value': "eyB1c2VyOjEgfQ$0:=="}))
        self.assertEqual(page, "[eyB1c2VyOjEgfQ$0:==]")
        page = self.template.render(Context({'value': "eyB1c2VyOjEgfQ==$0:"}))
        self.assertEqual(page, "[eyB1c2VyOjEgfQ==$0:]")
        page = self.template.render(Context({'value': "$0eyBwcm9mOjIgfQ=="}))
        self.assertEqual(page, "[$0eyBwcm9mOjIgfQ==]")
        page = self.template.render(Context({'value': "$0:eyBwcm9mOjIgfQ=="}))
        self.assertEqual(page, "[eyBwcm9mOjIgfQ==]")

        class Bin:
            def __str__(self):
                return "$0:325d9e0952d90d991034e223605a1a5f"
        page = self.template.render(Context({'value': Bin()}))
        self.assertEqual(page, "[325d9e0952d90d991034e223605a1a5f]")


@tag('templatetags')
class IsEsperantoSurrogateFilterTests(TestCase):
    template = Template(
        "{% load is_esperanto_surrogate from profile %}"
        "{{ value|is_esperanto_surrogate }}"
    )

    def test_negative(self):
        # The filter returns a Match object. When no Esperanto surrogate letters
        # are present, a None object is expected.
        page = self.template.render(Context({'value': ""}))
        self.assertEqual(page, str(None))
        page = self.template.render(Context({'value': "eĥoŜANĝo"}))
        self.assertEqual(page, str(None))
        page = self.template.render(Context({'value': "c'iuj'au'de"}))
        self.assertEqual(page, str(None))
        page = self.template.render(Context({'value': "ExoW^anThouh"}))
        self.assertEqual(page, str(None))

    def test_positive(self):
        for pre in product('ab', 'cCgGhHjJsSuU'):
            for post in product('hHxX^', 'QW'):
                if pre[1].lower() == 'u' and post[0].lower() == 'h':
                    post = ('~', post[1])
                v = ''.join(pre) + ''.join(post)
                with self.subTest(value=v):
                    page = self.template.render(Context({'value': v}))
                    self.assertNotEqual(page, str(None))
                    self.assertIn("re.Match object", page)
        for letter in 'cghjsu':
            for transform in ('lower', 'upper'):
                v = getattr('^' + letter + 'Yc', transform)()
                with self.subTest(value=v):
                    page = self.template.render(Context({'value': v}))
                    self.assertNotEqual(page, str(None))
                    self.assertIn("re.Match object", page)

    def test_ambiguous(self):
        # Since the filter is very simple, a few false positives are expected.
        for value in ("busHaltejo", "flughaveno", "les cheveux", "rue d'Animaux"):
            with self.subTest(value=value):
                page = self.template.render(Context({'value': value}))
                self.assertNotEqual(page, str(None))


@tag('templatetags')
class IconFilterTests(TestCase):
    @classmethod
    @modify_settings(INSTALLED_APPS={
        'append': 'tests.templatetags.test_profile_tags',
    })
    def setUpClass(cls):
        super().setUpClass()

        class DecoratedField(CharField):
            @property
            def icon(self):
                return "//ᐠ｡ꞈ｡ᐟ\\"

        class DecoratedModel(Model):
            cat = DecoratedField("oliver")
            cow = CharField("dottie")

            @property
            def icon(self):
                return "ᓚᘏᗢ"

        cls.DecoratedModel = DecoratedModel

    def test_model_icon(self):
        template = Template("{% load icon from profile %}[{{ obj|icon }}]")

        page = template.render(Context({'obj': None}))
        self.assertEqual(page, "[]")
        page = template.render(Context({'obj': object()}))
        self.assertEqual(page, "[]")
        page = template.render(Context({'obj': self.DecoratedModel()}))
        self.assertEqual(page, "[ᓚᘏᗢ]")

    def test_field_icon(self):
        template_string = string.Template(
            "{% load icon from profile %}"
            "[{{ obj|icon:'$FIELD' }}]")

        template = Template(template_string.substitute(FIELD='cat'))
        page = template.render(Context({'obj': self.DecoratedModel()}))
        self.assertEqual(page, "[//ᐠ｡ꞈ｡ᐟ\\]")

        template = Template(template_string.substitute(FIELD='cow'))
        page = template.render(Context({'obj': self.DecoratedModel()}))
        self.assertEqual(page, "[]")

        template = Template(template_string.substitute(FIELD='dog'))
        with self.assertRaises(FieldDoesNotExist):
            template.render(Context({'obj': self.DecoratedModel()}))


class MockPronounType(TextChoices):
    NEUTRAL = 'qwqw', "QwQw"
    ANY = '_any_', "Anyy"


@tag('templatetags')
@patch('hosting.models.Profile.Pronouns', MockPronounType)
class GetPronounFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.template = Template(
            "{% load get_pronoun from profile %}"
            "[{{ obj|get_pronoun }}]"
        )
        cls.profile = ProfileFactory()
        cls.context = Context({'obj': cls.profile})

    def test_sanity(self):
        # Sanity check.
        page = self.template.render(Context({'obj': None}))
        self.assertEqual(page, "[QwQw]")
        with self.assertRaises(AttributeError):
            self.template.render(Context({'obj': object()}))

    def test_undefined_pronoun(self):
        # For a profile with an undefined pronoun,
        # the expected result is the default neutral pronoun.
        self.profile.pronoun = ''
        page = self.template.render(self.context)
        self.assertEqual(page, "[QwQw]")

    def test_any_pronoun(self):
        # For a profile with a pronoun indicated as 'any',
        # the expected result is the default neutral pronoun.
        self.profile.pronoun = '_any_'
        page = self.template.render(self.context)
        self.assertEqual(page, "[QwQw]")

    def test_defined_pronoun(self):
        # For a profile with a defined pronoun, the expected result is the pronoun.
        self.profile.pronoun = 'elephant'
        page = self.template.render(self.context)
        self.assertEqual(page, "[elephant]")
        self.profile.pronoun = 'dog or cat'
        page = self.template.render(self.context)
        self.assertEqual(page, "[dog]")


@tag('templatetags')
class FormatPronounFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        template_string = string.Template(
            "{% load format_pronoun from profile %}"
            "[{{ obj|format_pronoun$TAG }}]"
        )
        cls.template_without_tag = Template(template_string.substitute(TAG=''))
        cls.template_with_tag = Template(template_string.substitute(TAG=':"xx"'))
        cls.profile = ProfileFactory()
        cls.context = Context({'obj': cls.profile})

    def test_sanity(self):
        # Sanity check.
        for template in self.template_without_tag, self.template_with_tag:
            for obj in None, object():
                with self.subTest(tpl=template.source, obj=obj):
                    with self.assertRaises(AttributeError):
                        template.render(Context({'obj': obj}))

    def test_undefined_pronoun(self):
        # For a profile with an undefined pronoun, the expected result is empty.
        self.profile.pronoun = ''
        page = self.template_without_tag.render(self.context)
        self.assertEqual(page, "[]")
        page = self.template_with_tag.render(self.context)
        self.assertEqual(page, "[]")

    def test_defined_pronoun(self):
        # For a profile with a defined pronoun,
        # the expected result is the pronoun. decorated by the tag.
        self.profile.pronoun = 'elephant'
        page = self.template_without_tag.render(self.context)
        self.assertEqual(page, "[<>Elephant</>]")
        page = self.template_with_tag.render(self.context)
        self.assertEqual(page, "[<xx>Elephant</xx>]")

    def test_defined_pronoun_choice(self):
        # For a profile with a defined pronoun choice,
        # the expected result is the pronoun parts, decorated by the tag.
        self.profile.pronoun = 'dog or cat'
        page = self.template_without_tag.render(self.context)
        self.assertEqual(page, "[<>Dog</> or <>Cat</>]")
        page = self.template_with_tag.render(self.context)
        self.assertEqual(page, "[<xx>Dog</xx> or <xx>Cat</xx>]")

        self.profile.pronoun = 'Y , X , Z'
        page = self.template_without_tag.render(self.context)
        self.assertEqual(page, "[<>Y</> , <>X</> , Z]")


@tag('templatetags')
class AvatarDimensionFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        template_string = string.Template(
            "{% load avatar_dimension from profile %}"
            "[{{ obj|avatar_dimension$SIZE }}]"
        )
        cls.template = Template(template_string.substitute(SIZE=''))
        cls.template_with_size = Template(template_string.substitute(SIZE=':76.54321'))
        fake = Faker._get_faker()
        cls.avatar = SimpleUploadedFile(
            fake.file_name(extension='png'), fake.image(image_format='png'), 'image/png')

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({'obj': object()}))

    def test_missing_profile(self):
        expected_result = "[width=\"100.00%\" height=\"100.00%\" data-square]"
        page = self.template.render(Context())
        self.assertEqual(page, expected_result)
        with override_settings(LANGUAGE_CODE='eo'):
            page = self.template.render(Context())
            self.assertEqual(page, expected_result)

    def test_missing_avatar(self):
        expected_result = "[width=\"100.00%\" height=\"100.00%\" data-square]"
        profile = ProfileFactory()
        context = Context({'obj': profile})

        page = self.template.render(context)
        self.assertEqual(page, expected_result)

        profile.avatar = self.avatar
        with patch('django.core.files.storage.FileSystemStorage.exists', return_value=False):
            page = self.template.render(context)
            self.assertEqual(page, expected_result)

            expected_result = "[width=\"76.54%\" height=\"76.54%\" data-square]"
            page = self.template_with_size.render(context)
            self.assertEqual(page, expected_result)
            with override_settings(LANGUAGE_CODE='eo'):
                page = self.template_with_size.render(context)
                self.assertEqual(page, expected_result)

    @override_settings(MEDIA_ROOT='tests/assets/')
    def test_present_avatar(self):
        profile = ProfileFactory()
        context = Context({'obj': profile})

        profile.avatar = 'b7044568.gif'
        page = self.template.render(context)
        self.assertEqual(page, "[height=\"100.00%\" data-wide]")
        page = self.template_with_size.render(context)
        self.assertEqual(page, "[height=\"76.54%\" data-wide]")

        profile.avatar = 'b7044569.gif'
        page = self.template.render(context)
        self.assertEqual(page, "[width=\"100.00%\" data-tall]")
        page = self.template_with_size.render(context)
        self.assertEqual(page, "[width=\"76.54%\" data-tall]")


@tag('templatetags')
class GetApproverTagTests(WebTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template_single = Template(
            "{% load get_approver from profile %}"
            "{% get_approver model %}"
        )
        cls.template_multiple = Template(
            "{% load get_approver from profile %}"
            "{% get_approver model_one %},"
            "{% get_approver model_two %},"
            "{% get_approver model_three %}"
        )

        class DummyView(generic.TemplateView):
            pass
        cls.DummyView = DummyView

    @classmethod
    def setUpTestData(cls):
        cls.profiles = ProfileFactory.create_batch(3)
        cls.approvers = UserFactory.create_batch(2, profile=None)

    def test_no_approver(self):
        # When there is no model instance or no supervisor checked the
        # model instance, the expected result is None object.
        page = self.template_single.render(Context())
        self.assertEqual(page, str(None))

        self.profiles[0].checked_by_id = None
        page = self.template_single.render(Context({'model': self.profiles[0]}))
        self.assertEqual(page, str(None))

    def test_approver_current_user(self):
        # When the model instance was checked by the current user (already in the
        # context of the view), the expected result is that user's object and no
        # additional queries performed on the database.
        for i in range(len(self.profiles)):
            self.profiles[i].checked_by_id = self.approvers[0].pk
        with self.assertNumQueries(0):
            page = self.template_single.render(
                Context({
                    'model': self.profiles[0],
                    'user': self.approvers[0],
                    'view': self.DummyView.as_view(),
                })
            )
        self.assertEqual(page, self.approvers[0].username)
        with self.assertNumQueries(0):
            page = self.template_multiple.render(
                Context({
                    'model_one': self.profiles[0],
                    'model_two': self.profiles[1],
                    'model_three': self.profiles[2],
                    'user': self.approvers[0],
                    'view': self.DummyView.as_view(),
                })
            )
        self.assertEqual(page, ",".join([self.approvers[0].username] * 3))

    def test_single_approver(self):
        # When several model instances were checked by the same user,
        # the expected result is that user's object and a single database query
        # to fetch the object.
        for i in range(len(self.profiles)):
            self.profiles[i].checked_by_id = self.approvers[1].pk
        with self.assertNumQueries(1):
            page = self.template_multiple.render(
                Context({
                    'model_one': self.profiles[0],
                    'model_two': self.profiles[1],
                    'model_three': self.profiles[2],
                    'view': self.DummyView.as_view(),
                })
            )
        self.assertEqual(page, ",".join([self.approvers[1].username] * 3))

    def test_multiple_approvers(self):
        # When several model instances were checked by two different users,
        # the expected result is these users' objects and only two database
        # queries to fetch the objects.
        self.profiles[0].checked_by_id = self.approvers[1].pk
        self.profiles[1].checked_by_id = self.approvers[0].pk
        self.profiles[2].checked_by_id = self.approvers[1].pk
        user = UserFactory(profile=None)

        with self.assertNumQueries(2):
            page = self.template_multiple.render(
                Context({
                    'model_one': self.profiles[2],
                    'model_two': self.profiles[1],
                    'model_three': self.profiles[0],
                    'user': user,
                    'view': self.DummyView.as_view(),
                })
            )
        self.assertEqual(page, ",".join(self.approvers[i].username for i in (1, 0, 1)))


@tag('templatetags')
class IsSupervisorFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.template = Template(
            "{% load is_supervisor from profile %}"
            "{{ person|is_supervisor }}"
        )
        cls.country_group = Group.objects.get_or_create(name='NL')[0]

    def perform_tests_of_user(self, user, expected_result):
        with self.assertLogs('PasportaServo.auth', level='DEBUG') as cm:
            page = self.template.render(Context({'person': user}))
            self.assertEqual(page, str(expected_result))
            page = self.template.render(Context({'person': user.profile}))
            self.assertEqual(page, str(expected_result))
        self.assertIn("checking if supervising", cm.output[0])
        self.assertIn(user.username, cm.output[0])

    def test_regular_user(self):
        # The expected result for non-supervisor (referred as user or profile)
        # is False.
        user = UserFactory()
        self.perform_tests_of_user(user, False)

    def test_supervisor_user(self):
        # The expected result for a supervisor (referred as user or profile)
        # is True.
        user = UserFactory()
        self.country_group.user_set.add(user)
        self.perform_tests_of_user(user, True)

    def test_inactive_supervisor_user(self):
        # The expected result for a supervisor with an inactive account
        # (referred as user or profile) is False.
        user = UserFactory(is_active=False)
        self.country_group.user_set.add(user)
        self.perform_tests_of_user(user, False)

    def test_admin_user(self):
        user = UserFactory(is_superuser=True)
        self.perform_tests_of_user(user, True)

    def test_sanity(self):
        # The expected result for a profile without account is False.
        page = self.template.render(Context({'person': ProfileSansAccountFactory()}))
        self.assertEqual(page, str(False))
        # The expected result for an anonymous user is False.
        page = self.template.render(Context({'person': AnonymousUser()}))
        self.assertEqual(page, str(False))


@tag('templatetags')
class IsSupervisorOfFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.template = Template(
            "{% load is_supervisor_of from profile %}"
            "{{ person|is_supervisor_of:obj }}"
        )
        cls.template_error = (
            "Supervisor check needs either a profile, "
            "a country, or a list of countries."
        )

        cls.family_member = ProfileSansAccountFactory()
        (
            cls.profile_simple,
            cls.profile_complex_active,
            cls.profile_complex_inactive,
            cls.profile_complex_deleted,
        ) = ProfileFactory.create_batch(4)
        PlaceFactory(owner=cls.profile_complex_active, country='NL')
        PlaceFactory(
            owner=cls.profile_complex_inactive, country='NL',
            deleted_on=timezone.now())
        cls.profile_complex_deleted.deleted_on = timezone.now()
        PlaceFactory(owner=cls.profile_complex_deleted, country='NL')

        (
            cls.regular_user,               # Not a supervisor.
            cls.supervisor_user,            # Supervisor in NL.
            cls.inactive_supervisor_user,   # Supervisor in NL, not active.
            cls.supervisor_2c_user,         # Supervisor in NL and 1 other country.
            cls.supervisor_3c_user,         # Supervisor in 3 countries but not NL.
            cls.admin_user,                 # Superuser; supervises everywhere.
        ) = UserFactory.create_batch(6)
        Group.objects.get_or_create(name='NL')[0].user_set.add(
            cls.supervisor_user, cls.inactive_supervisor_user, cls.supervisor_2c_user)
        cls.inactive_supervisor_user.is_active = False
        cls.countries = sample(set(COUNTRIES) - {'NL'}, 3)
        Group.objects.get_or_create(name=cls.countries[1])[0].user_set.add(
            cls.supervisor_2c_user, cls.supervisor_3c_user)
        for i in (0, 2):
            Group.objects.get_or_create(name=cls.countries[i])[0].user_set.add(
                cls.supervisor_3c_user)
        cls.admin_user.is_superuser = True

        for backend in get_backends():
            try:
                cls.auth_backend_method = backend.is_user_supervisor_of
            except AttributeError:
                pass

    def perform_tests_on_object(self, obj, obj_tag, is_supervised, skip_backend_tests=False):
        context = Context({'obj': obj})
        try:
            is_supervised, is_administered = is_supervised['sv'], is_supervised['su']
        except TypeError:
            is_administered = is_supervised
        test_data = [
            # The expected result for a non-authenticated user is False.
            (AnonymousUser(), 'anonymous', [False]),
            # The expected result for non-supervisor is False.
            (self.regular_user, 'regular', [False]),
            # The expected result for an NL supervisor is dependent on the object.
            (self.supervisor_user, 'NL supervisor', [is_supervised]),
            # The expected result for an inactive NL supervisor is False via the
            # template tag, and dependent on object via direct auth backend call.
            (self.inactive_supervisor_user, 'inactive NL supervisor',
             [False, is_supervised]),
            # The expected result for a supervisor in NL (among others)
            # is dependent on the object.
            (self.supervisor_2c_user, 'NL+1 supervisor', [is_supervised]),
            # The expected result for a supervisor but not in NL is False.
            (self.supervisor_3c_user, 'not NL supervisor',
             [False if is_supervised is not None else None]),
            # The expected result for a superuser is always True via the
            # template tag, and dependent on object via direct auth backend call.
            (self.admin_user, 'superuser', [True, is_administered]),
            # The expected result for a profile without account is False.
            (self.family_member, 'w/o account', [False]),
        ]

        for user, user_tag, expected_result in test_data:
            with self.subTest(user=user_tag, obj=obj_tag, expected=expected_result):
                self.perform_tests_of_user(
                    user, context, skip_backend_tests, *expected_result)

    def perform_tests_of_user(
            self, user, context, skip_backend_tests,
            expected_result, expected_backend_result=None
    ):
        if expected_backend_result is None:
            expected_backend_result = expected_result

        with self.assertLogs('PasportaServo.auth', level='DEBUG') as cm:
            # Verify for a User object.
            context['person'] = user
            if expected_result is None:
                with self.assertRaisesMessage(Exception, self.template_error):
                    page = self.template.render(context)
            else:
                page = self.template.render(context)
                self.assertEqual(page, str(expected_result))

            # Verify for a Profile object.
            if not isinstance(user, Profile) and hasattr(user, 'profile'):
                context['person'] = user.profile
                if expected_result is None:
                    with self.assertRaisesMessage(Exception, self.template_error):
                        page = self.template.render(context)
                else:
                    page = self.template.render(context)
                    self.assertEqual(page, str(expected_result))

        # Verify log.
        self.assertIn("checking if object is supervised", cm.output[0])
        if not isinstance(user, Profile):
            self.assertIn(user.username, cm.output[0])

        # Verify directly for the underlying auth backend's method.
        if (not skip_backend_tests and hasattr(self, 'auth_backend_method')
                and not isinstance(user, Profile)):
            self.assertEqual(
                self.auth_backend_method(user, context['obj']),
                expected_backend_result
            )

    def test_via_invalid_object(self):
        self.perform_tests_on_object(object(), 'generic object', None, True)
        self.perform_tests_on_object(AnonymousUser(), 'anon user', None, True)
        if hasattr(self, 'auth_backend_method'):
            with self.assertRaisesMessage(Exception, self.template_error):
                self.auth_backend_method(AnonymousUser(), None)
            with self.assertRaisesMessage(Exception, self.template_error):
                self.auth_backend_method(self.admin_user, None)

    def test_via_profile(self):
        self.perform_tests_on_object(self.profile_simple, 'simple profile', False)
        self.perform_tests_on_object(
            self.profile_complex_active, 'complex profile', True)
        self.perform_tests_on_object(
            self.profile_complex_inactive, 'complex (inactive) profile', False)
        self.perform_tests_on_object(
            self.profile_complex_deleted, 'complex (deleted) profile', True)
        self.perform_tests_on_object(self.family_member, 'family member', False)

    def test_via_profile_id(self):
        self.perform_tests_on_object(
            self.profile_simple.pk, 'simple profile', False, True)
        self.perform_tests_on_object(
            self.profile_complex_active.pk, 'complex profile', True, True)
        self.perform_tests_on_object(
            self.profile_complex_inactive.pk, 'complex (inactive) profile', False, True)
        self.perform_tests_on_object(
            self.profile_complex_deleted.pk, 'complex (deleted) profile', True, True)
        self.perform_tests_on_object(
            self.family_member.pk, 'family member', False, True)
        self.perform_tests_on_object(-1, 'non-existent profile', False, True)

    def test_via_place(self):
        self.perform_tests_on_object(
            self.profile_complex_active.owned_places.first(), 'place', True)
        self.perform_tests_on_object(
            self.profile_complex_inactive.owned_places.first(), 'deleted place', True)

    def test_via_country(self):
        self.perform_tests_on_object(
            self.profile_complex_active.owned_places.first().country,
            'supervised_country', True)
        self.perform_tests_on_object(
            Country(choice(list(set(COUNTRIES) - set(self.countries) - {'NL'}))),
            'unsupervised_country', {'sv': False, 'su': True})

    def test_via_list_of_countries(self):
        self.perform_tests_on_object("", 'empty string', False, True)
        self.perform_tests_on_object([], 'empty list', False)
        self.perform_tests_on_object([""], 'list of empty string', False)
        self.perform_tests_on_object("NL", 'string "NL"', True, True)
        self.perform_tests_on_object(["NL"], 'list of string "NL"', True)

        unsupervised_countries = sample(set(COUNTRIES) - set(self.countries) - {'NL'}, 2)
        unsupervised_countries_string = " , ".join(unsupervised_countries)
        mixed_countries = unsupervised_countries + ["NL"]
        mixed_countries_string = "  ".join(mixed_countries)
        mixed_countries = [Country(c) for c in mixed_countries]

        self.perform_tests_on_object(
            mixed_countries_string,
            f'string "{mixed_countries_string}"', True, True)
        self.perform_tests_on_object(
            mixed_countries,
            f'list {mixed_countries}', True)
        self.perform_tests_on_object(
            unsupervised_countries_string,
            f'string "{unsupervised_countries_string}"', False, True)
        self.perform_tests_on_object(
            unsupervised_countries,
            f'list {unsupervised_countries}', {'sv': False, 'su': True})

    def test_list_of_invalid_objects(self):
        # The expected result for any user (including supervisor) is False.
        # This is because when a list is given, it should contain country
        # ISO codes only.
        context = Context({
            'obj': [object(), 17.3, AnonymousUser(), SimpleUploadedFile('abc.xyz', None)],
            'person': self.supervisor_2c_user,
        })
        page = self.template.render(context)
        self.assertEqual(page, str(False))
        # The only exception is a superuser, who by default has all permissions.
        context['person'] = self.admin_user
        page = self.template.render(context)
        self.assertEqual(page, str(True))


@tag('templatetags')
class SupervisorOfFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.template = Template(
            "{% load supervisor_of from profile %}"
            "{{ person|supervisor_of|safe }}"
        )

        cls.family_member = ProfileSansAccountFactory()
        (
            cls.regular_user,               # Not a supervisor.
            cls.supervisor_user,            # Supervisor in 3 countries.
            cls.inactive_supervisor_user,   # Supervisor, not active.
            cls.admin_user,                 # Superuser; supervises everywhere.
        ) = UserFactory.create_batch(4)
        cls.countries = sample(list(COUNTRIES), 3)
        for c in cls.countries:
            Group.objects.get_or_create(name=c)[0].user_set.add(
                cls.supervisor_user, cls.inactive_supervisor_user)
        cls.inactive_supervisor_user.is_active = False
        cls.admin_user.is_superuser = True

        for backend in get_backends():
            try:
                cls.auth_backend_method = backend.get_user_supervisor_of
            except AttributeError:
                pass

    def test_supervisor_backend(self):
        country_names = sorted(all_countries.name(code) for code in self.countries)
        test_data = [
            # The expected result for a non-authenticated user is empty list.
            (AnonymousUser(), 'anonymous', []),
            # The expected result for non-supervisor is empty list.
            (self.regular_user, 'regular', []),
            # The expected result for a supervisor
            # is list of supervised by them country names.
            (self.supervisor_user, 'supervisor', country_names),
            # The expected result for an inactive supervisor
            # is list of supervised by them country names.
            (self.inactive_supervisor_user, 'inactive supervisor', country_names),
            # The expected result for a superuser is list of all country names.
            (self.admin_user, 'superuser',
             sorted(next(all_countries.translate_code(c)).name for c in COUNTRIES)),
            # The expected result for a profile without account is empty list.
            (self.family_member, 'w/o account', []),
        ]

        for user, user_tag, expected_result in test_data:
            with self.subTest(user=user_tag):
                with self.assertLogs('PasportaServo.auth', level='DEBUG') as cm:
                    # Verify for a User object.
                    page = self.template.render(Context({'person': user}))
                    self.assertEqual(page, str(expected_result))

                    # Verify for a Profile object.
                    if not isinstance(user, Profile) and hasattr(user, 'profile'):
                        page = self.template.render(Context({'person': user.profile}))
                        self.assertEqual(page, str(expected_result))

                # Verify log.
                self.assertIn("searching supervised objects", cm.output[0])
                if not isinstance(user, Profile):
                    self.assertIn(user.username, cm.output[0])

                # Verify directly for the underlying auth backend's method.
                if hasattr(self, 'auth_backend_method') and not isinstance(user, Profile):
                    self.assertEqual(
                        set(self.auth_backend_method(user)),
                        set(expected_result)
                    )

    @override_settings(
        AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'])
    def test_default_backend(self):
        # The expected result for any user authenticated via a backend that does
        # not support supervising permissions, is an empty list.
        test_data = [
            (AnonymousUser(), 'anonymous'),
            (self.regular_user, 'regular'),
            (self.supervisor_user, 'supervisor'),
            (self.inactive_supervisor_user, 'inactive supervisor'),
            (self.admin_user, 'superuser'),
            (self.family_member, 'w/o account'),
        ]

        for user, user_tag in test_data:
            with self.subTest(user=user_tag):
                # Verify for a User object.
                page = self.template.render(Context({'person': user}))
                self.assertEqual(page, "[]")

                # Verify for a Profile object.
                if not isinstance(user, Profile) and hasattr(user, 'profile'):
                    page = self.template.render(Context({'person': user.profile}))
                    self.assertEqual(page, "[]")
