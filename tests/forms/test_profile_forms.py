from datetime import date, timedelta
from typing import Any, NamedTuple, Optional
from unittest.mock import patch

from django.core.exceptions import NON_FIELD_ERRORS
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.test import override_settings, tag
from django.urls import reverse

import rstr
from django_webtest import WebTest
from factory import Faker

from core.models import SiteConfiguration
from hosting.forms.profiles import (
    PreferenceOptinsForm, ProfileCreateForm,
    ProfileEmailUpdateForm, ProfileForm,
)
from hosting.models import PasportaServoUser, Profile
from hosting.widgets import ClearableWithPreviewImageInput

from .. import with_type_hint
from ..assertions import AdditionalAsserts
from ..factories import LocaleFaker, ProfileFactory, UserFactory
from .test_auth_forms import EmailUpdateFormTests


class ProfileFormTestingBase(AdditionalAsserts, with_type_hint(WebTest)):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host_required_fields = [
            'birth_date',
        ]
        cls.book_required_fields = [
            'birth_date',
            'gender',
            'first_name',
            'last_name',
        ]
        cls.config = SiteConfiguration.get_solo()
        cls.faker = Faker._get_faker()

    @classmethod
    def setUpTestData(cls):
        TaggedProfile = NamedTuple('TaggedProfile', [('obj', Profile), ('tag', str)])

        cls.profile_with_no_places = TaggedProfile(ProfileFactory.create(), "simple")
        profile = ProfileFactory.create(deceased=True)
        cls.profile_with_no_places_deceased = TaggedProfile(profile, "deceased")

        profile = ProfileFactory.create(places=[
            {'available': True},
        ])
        cls.profile_hosting = TaggedProfile(profile, "hosting")

        profile = ProfileFactory.create(places=[
            {'available': False, 'have_a_drink': True},
        ])
        cls.profile_meeting = TaggedProfile(profile, "meeting")

        profile = ProfileFactory.create(places=[
            {'available': True},
            {'available': False, 'tour_guide': True},
        ])
        cls.profile_hosting_and_meeting = TaggedProfile(profile, "hosting & meeting")

        profile = ProfileFactory.create(places=[
            {'available': True, 'in_book': True},
        ])
        cls.profile_in_book = TaggedProfile(profile, "in book (simple)")

        profile = ProfileFactory.create(places=[
            {'available': True, 'in_book': True},
            {'available': True, 'in_book': False},
            {'available': False, 'have_a_drink': True, 'in_book': False},
        ])
        cls.profile_in_book_complex = TaggedProfile(profile, "in book (complex)")

    def _init_form(
            self,
            data: Optional[dict[str, Any]] = None,
            files: Optional[dict[str, UploadedFile | None]] = None,
            instance: Optional[Profile] = None,
            empty: bool = False,
            save: bool = False,
            user: Optional[PasportaServoUser] = None,
    ) -> ProfileForm:
        ...

    def test_init(self):
        form_empty = self._init_form(empty=True, user=self.profile_with_no_places.obj.user)
        expected_fields = [
            'title',
            'first_name',
            'last_name',
            'names_inversed',
            'gender',
            'pronoun',
            'birth_date',
            'description',
            'avatar',
        ]
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(expected_fields), set(form_empty.fields))

        # Verify that fields are not unnecessarily marked 'required'.
        for form in (form_empty, self._init_form(instance=self.profile_with_no_places.obj)):
            for field in set(self.host_required_fields) | set(self.book_required_fields):
                with self.subTest(field=field):
                    self.assertFalse(form.fields[field].required)

        # Verify widgets.
        self.assertIsInstance(form_empty.fields['avatar'].widget, ClearableWithPreviewImageInput)

        # Verify that the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form_empty.save, 'alters_data')
            or hasattr(form_empty.save, 'do_not_call_in_templates')
        )

    def test_blank_data(self):
        # Empty form is expected to be valid.
        form = self._init_form({}, empty=True, user=self.profile_with_no_places.obj.user)
        self.assertTrue(form.is_valid())

        # Empty form for simple profile is expected to be valid.
        form = self._init_form({}, empty=True, instance=self.profile_with_no_places.obj)
        self.assertTrue(form.is_valid())

    def test_invalid_birth_date_in_future_or_past(self):
        # An overly young (born in future) or a too old profile is expected to be invalid.
        today = date.today()
        try:
            max_past = today.replace(year=today.year - 200)
        except ValueError:
            max_past = today.replace(year=today.year - 200, day=today.day - 1)
        for birth_date, violation_type in ([today + timedelta(days=1), "too unborn"],
                                           [max_past - timedelta(days=1), "too dead"]):
            for profile, profile_tag in (self.profile_with_no_places,
                                         self.profile_with_no_places_deceased,
                                         self.profile_hosting,
                                         self.profile_meeting,
                                         self.profile_hosting_and_meeting,
                                         self.profile_in_book,
                                         self.profile_in_book_complex):
                with self.subTest(condition=profile_tag, birth_date=birth_date, violation=violation_type):
                    form = self._init_form(
                        {
                            'first_name': "Aa",
                            'last_name': "Bb",
                            'birth_date': birth_date,
                            'gender': "undefined",
                        },
                        instance=profile)
                    self.assertFalse(form.is_valid())
                    self.assertIn('birth_date', form.errors)
                    if violation_type == "too unborn":
                        if profile_tag == "simple" or type(form) is ProfileCreateForm:
                            expected_errors = {
                                'en': "Ensure this value is less than or equal to {}.",
                                'eo': "Certigu ke ĉi tiu valoro estas malpli ol aŭ egala al {}.",
                            }
                            for lang in expected_errors:
                                with override_settings(LANGUAGE_CODE=lang):
                                    self.assertEqual(
                                        form.errors,
                                        {
                                            'birth_date': [expected_errors[lang].format(today)],
                                        }
                                    )
                        elif profile_tag == "deceased":
                            expected_errors = {
                                'en': ("The indicated date of birth is in conflict with the date of death"
                                       " ({:%Y-%m-%d})."),
                                'eo': ("La indikita dato de naskiĝo konfliktas kun la dato de forpaso"
                                       " ({:%Y-%m-%d})."),
                            }
                            for lang in expected_errors:
                                with override_settings(LANGUAGE_CODE=lang):
                                    self.assertEqual(
                                        form.errors,
                                        {
                                            'birth_date': [expected_errors[lang].format(profile.death_date)],
                                        }
                                    )
                        else:
                            expected_errors = {
                                'en': ("The minimum age to be allowed ", " is "),
                                'eo': ("Vi ekpovos ", " kiam estos "),
                            }
                            for lang in expected_errors:
                                with override_settings(LANGUAGE_CODE=lang):
                                    self.assertTrue(
                                        any(
                                            err.startswith(expected_errors[lang][0])
                                            and (expected_errors[lang][1] in err)
                                            for err in form.errors['birth_date']
                                        ),
                                        msg="Form field 'birth_date' error does not indicate minimum age."
                                    )
                    if violation_type == "too dead":
                        expected_errors = {
                            'en': "Ensure this value is greater than or equal to {}.",
                            'eo': "Certigu ke ĉi tiu valoro estas pli ol aŭ egala al {}.",
                        }
                        for lang in expected_errors:
                            with override_settings(LANGUAGE_CODE=lang):
                                self.assertEqual(
                                    form.errors,
                                    {
                                        'birth_date': [expected_errors[lang].format(max_past)],
                                    }
                                )

    def test_valid_birth_date(self):
        # A very young profile of a user who neither hosts nor meets visitors is expected to be valid.
        form = self._init_form(
            {
                'first_name': "Aa",
                'last_name': "Bb",
                'birth_date': self.faker.date_between(start_date='-16y', end_date=date.today()),
            },
            instance=self.profile_with_no_places.obj)
        self.assertTrue(form.is_valid())

        # A young profile of a deceased user who neither hosted nor met visitors is expected to be valid.
        form = self._init_form(
            {
                'first_name': "Aa",
                'last_name': "Bb",
                'birth_date': self.faker.date_between(start_date='-22y', end_date='-11y'),
            },
            instance=self.profile_with_no_places_deceased.obj)
        self.assertTrue(form.is_valid())

    def test_invalid_names(self):
        # A profile with names containing non-latin characters or digits is expected to be invalid.
        zh_faker = LocaleFaker._get_faker(locale='zh')
        id_faker = LocaleFaker._get_faker(locale='id')
        tr_faker = LocaleFaker._get_faker(locale='tr')
        test_data = (
            (
                "latin name",
                lambda: zh_faker.name(),
                {
                    'en': "provide this data in Latin characters",
                    'eo': "indiku tiun ĉi informon per latinaj literoj",
                },
            ), (
                "symbols",
                lambda: rstr.punctuation(2) + rstr.punctuation(6, 10, include=rstr.lowercase(4)),
                {
                    'en': "provide this data in Latin characters",
                    'eo': "indiku tiun ĉi informon per latinaj literoj",
                },
            ), (
                "digits",
                lambda: rstr.lowercase(8, 12, include=set(rstr.digits())),
                {
                    'en': "Digits are not allowed",
                    'eo': "Ciferoj ne estas permesitaj",
                },
            ), (
                "all caps",
                lambda: rstr.uppercase(8, 12),
                {
                    'en': "Today is not CapsLock day",
                    'eo': "La CapsLock-tago ne estas hodiaŭ",
                },
            ), (
                "many caps",
                lambda: rstr.uppercase(8, 12, include=rstr.lowercase(5)),
                {
                    'en': "there are too many uppercase letters",
                    'eo': "estas tro da majuskloj",
                },
            ), (
                "many caps w/prefix",
                lambda: "Mac" + rstr.uppercase(2) + rstr.lowercase(5),
                {
                    'en': "there are too many uppercase letters",
                    'eo': "estas tro da majuskloj",
                },
            )
        )

        for field_violation, field_value, assert_content in test_data:
            for wrong_field in ('first_name', 'last_name'):
                for profile, profile_tag in (self.profile_with_no_places,
                                             self.profile_hosting,
                                             self.profile_meeting,
                                             self.profile_hosting_and_meeting,
                                             self.profile_in_book,
                                             self.profile_in_book_complex):
                    with self.subTest(condition=profile_tag, field=wrong_field, violation=field_violation):
                        data = {
                            'first_name': id_faker.first_name(),
                            'last_name': tr_faker.last_name(),
                            'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                            'gender': self.faker.word(),
                        }
                        data[wrong_field] = field_value()
                        with self.subTest(value=data[wrong_field]):
                            form = self._init_form(data, instance=profile)
                            self.assertFalse(form.is_valid())
                            self.assertIn(wrong_field, form.errors)
                            for lang in assert_content:
                                with override_settings(LANGUAGE_CODE=lang):
                                    self.assertTrue(
                                        any(
                                            assert_content[lang] in error
                                            for error in form.errors[wrong_field]
                                        ),
                                        msg=repr(form.errors)
                                    )

    def test_valid_names(self):
        # A profile with only one of the names of a user who wishes to host or meet visitors
        # is expected to be valid.
        en_faker = LocaleFaker._get_faker(locale='en')
        for profile, profile_tag in (self.profile_hosting,
                                     self.profile_meeting,
                                     self.profile_hosting_and_meeting):
            with self.subTest(condition=profile_tag, name="first name"):
                form = self._init_form(
                    {
                        'first_name': en_faker.first_name(),
                        'last_name': "",
                        'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                    },
                    instance=profile)
                self.assertTrue(form.is_valid())
            with self.subTest(condition=profile_tag, name="last name"):
                form = self._init_form(
                    {
                        'first_name': "",
                        'last_name': en_faker.last_name(),
                        'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                    },
                    instance=profile)
                self.assertTrue(form.is_valid())

    @tag('avatar')
    def test_invalid_avatar(self):
        # An invalid image binary is expected to be rejected.
        test_data = [
            SimpleUploadedFile(
                self.faker.file_name(extension='jpeg'), self.faker.binary(length=256), 'image/jpeg'),
            SimpleUploadedFile(
                self.faker.file_name(extension='PNG'), bytes(self.faker.sentence(), 'UTF-8'), 'text/plain')
        ]
        for data in test_data:
            with self.subTest(file=repr(data), violation='non-image'):
                form = self._init_form(files={'avatar': data}, instance=self.profile_with_no_places.obj)
                self.assertFalse(form.is_valid())
                self.assertIn('avatar', form.errors)
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(
                        form.errors['avatar'],
                        [
                            "Upload a valid image. The file you uploaded was "
                            "either not an image or a corrupted image."
                        ]
                    )
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertEqual(
                        form.errors['avatar'],
                        [
                            "Alŝutu validan bildon. La alŝutita dosiero ne estas "
                            "bildo, aŭ estas difektita bildo."
                        ]
                    )

        # An invalid file mime type is expected to be rejected.
        with open('tests/assets/c325d34f.mpg', 'rb') as fh:
            data = SimpleUploadedFile(self.faker.file_name(category='image'), fh.read())
        with self.subTest(file=repr(data), violation='content-type'):
            form = self._init_form(files={'avatar': data}, instance=self.profile_with_no_places.obj)
            self.assertFalse(form.is_valid())
            self.assertIn('avatar', form.errors)
            with override_settings(LANGUAGE_CODE='en'):
                self.assertIn("File type is not supported.", form.errors['avatar'])
            with override_settings(LANGUAGE_CODE='eo'):
                self.assertIn("Dosiertipo ne akceptebla.", form.errors['avatar'])

        # An empty image file is expected to be rejected.
        data = SimpleUploadedFile(self.faker.file_name(category='image'), b'', 'image/png')
        with self.subTest(file=repr(data), violation='empty', size=data.size):
            form = self._init_form(files={'avatar': data}, instance=self.profile_with_no_places.obj)
            self.assertFalse(form.is_valid())
            self.assertIn('avatar', form.errors)
            with override_settings(LANGUAGE_CODE='en'):
                self.assertEqual(form.errors['avatar'], ["The submitted file is empty."])
            with override_settings(LANGUAGE_CODE='eo'):
                self.assertEqual(form.errors['avatar'], ["La alŝutita dosiero estas malplena."])

        # A too-large file is expected to be rejected.
        with open('tests/assets/b7044568.gif', 'rb') as fh:
            data = SimpleUploadedFile(self.faker.file_name(category='image'), fh.read())
        with self.subTest(file=repr(data), violation='size', size=data.size):
            form = self._init_form(files={'avatar': data}, instance=self.profile_with_no_places.obj)
            self.assertFalse(form.is_valid())
            self.assertIn('avatar', form.errors)
            with override_settings(LANGUAGE_CODE='en'):
                self.assertStartsWith(
                    form.errors['avatar'][0],
                    "Please keep file size under 100.0 KB."
                )
            with override_settings(LANGUAGE_CODE='eo'):
                self.assertStartsWith(
                    form.errors['avatar'][0],
                    "Bv. certigu ke dosiergrando estas sub 100,0 KB."
                )

    @tag('avatar')
    def test_valid_avatar(self):
        data = SimpleUploadedFile(
            self.faker.file_name(category='image'), self.faker.image(size=(150, 160), image_format='webp'))
        form = self._init_form(files={'avatar': data}, instance=self.profile_with_no_places.obj)
        self.assertTrue(form.is_valid(), msg=repr(form.errors))

    def test_valid_data_for_simple_profile(self):
        form = self._init_form({}, instance=self.profile_with_no_places.obj, save=True)
        self.assertTrue(form.is_valid())
        profile = form.save(commit=False)
        if type(form) is ProfileForm:
            self.assertIs(profile, self.profile_with_no_places.obj)
        elif type(form) is ProfileCreateForm:
            self.assertIsNot(profile, self.profile_with_no_places.obj)
            self.assertIs(profile.user, form.user)
        self.assertEqual(profile.first_name, "")
        self.assertEqual(profile.last_name, "")
        self.assertFalse(profile.names_inversed)
        self.assertEqual(profile.title, "")
        self.assertIsNone(profile.gender)
        self.assertEqual(profile.pronoun, "")
        self.assertIsNone(profile.birth_date)
        self.assertEqual(profile.description, "")
        self.assertEqual(profile.avatar.name, "")

    @override_settings(MEDIA_ROOT='tests/assets/')
    @patch('django.core.files.storage.FileSystemStorage.save', return_value='a2529045.jpg')
    def test_valid_data(self, profile, profile_tag, mock_storage_save):
        fr_faker = LocaleFaker._get_faker(locale='fr')
        es_faker = LocaleFaker._get_faker(locale='es')
        for dataset_type in ("full", "partial"):
            data = {
                'title': "",
                'first_name': fr_faker.first_name(),
                'last_name': es_faker.last_name(),
                'names_inversed': self.faker.boolean(),
                'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                'description': "",
                'gender': self.faker.word() if "in book" in profile_tag else None,
                'pronoun': None,
                'avatar': None,
            }
            if dataset_type == "full":
                avatar_file = SimpleUploadedFile(
                    self.faker.file_name(extension='pcx'), self.faker.image(size=(10, 10), image_format='pcx')
                )
                data.update({
                    'title': self.faker.random_element(elements=filter(None, profile.Titles.values)),
                    'description': self.faker.text(),
                    'gender': self.faker.word(),
                    'pronoun': self.faker.random_element(elements=profile.Pronouns.values),
                    'avatar': avatar_file,
                })
            with self.subTest(dataset=dataset_type, condition=profile_tag):
                avatar_file = data.pop('avatar', None)
                form = self._init_form(
                    {**data, 'avatar-clear': avatar_file is None},
                    files={'avatar': avatar_file},
                    instance=profile,
                    save=True)
                self.assertTrue(form.is_valid())
                saved_profile = form.save()
                if type(form) is ProfileForm:
                    self.assertIs(saved_profile, profile)
                elif type(form) is ProfileCreateForm:
                    self.assertIs(saved_profile.user, form.user)
                for field in data:
                    with self.subTest(field=field):
                        if field == 'gender':
                            self.assertEqual(getattr(saved_profile, field), data[field])
                        elif field == 'avatar':
                            self.assertEqual(
                                saved_profile.avatar.name,
                                mock_storage_save.return_value if avatar_file is not None else ""
                            )
                        else:
                            self.assertEqual(
                                getattr(saved_profile, field),
                                data[field] if data[field] is not None else ""
                            )


@tag('forms', 'forms-profile', 'profile')
class ProfileFormTests(ProfileFormTestingBase, WebTest):
    def _init_form(self, data=None, files=None, instance=None, empty=False, save=False, user=None):
        if not empty:
            assert instance is not None
        return ProfileForm(data=data, files=files, instance=instance)

    def test_init(self):
        super().test_init()

        # Verify that fields are marked 'required' when user is hosting or meeting.
        for profile, profile_tag in (self.profile_hosting,
                                     self.profile_meeting,
                                     self.profile_hosting_and_meeting):
            form = self._init_form(instance=profile)
            for field in self.host_required_fields:
                with self.subTest(condition=profile_tag, field=field):
                    self.assertTrue(form.fields[field].required)

        # Verify that fields are marked 'required' when user is in the printed edition.
        for profile, profile_tag in (self.profile_in_book,
                                     self.profile_in_book_complex):
            form = self._init_form(instance=profile)
            for field in self.book_required_fields:
                with self.subTest(condition=profile_tag, field=field):
                    self.assertTrue(form.fields[field].required)

    def test_blank_data_for_complex_profile(self):
        # Empty form for complex profile (hosting or meeting or in book) is expected to be invalid.
        for profile, profile_tag in (self.profile_hosting,
                                     self.profile_meeting,
                                     self.profile_hosting_and_meeting):
            with self.subTest(condition=profile_tag):
                form = self._init_form({}, instance=profile)
                self.assertFalse(form.is_valid())
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(
                        form.errors,
                        {
                            NON_FIELD_ERRORS: ["Please indicate how guests should name you"],
                            'birth_date': ["This field is required."],
                        }
                    )
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertEqual(
                        form.errors,
                        {
                            NON_FIELD_ERRORS: ["Bonvole indiku kiel gastoj nomu vin"],
                            'birth_date': ["Ĉi tiu kampo estas deviga."],
                        }
                    )
        for profile, profile_tag in (self.profile_in_book,
                                     self.profile_in_book_complex):
            with self.subTest(condition=profile_tag):
                form = self._init_form({}, instance=profile)
                self.assertFalse(form.is_valid())
                self.assertEqual(set(form.errors.keys()), set(self.book_required_fields + [NON_FIELD_ERRORS]))
                for field in self.book_required_fields:
                    with self.subTest(field=field):
                        with override_settings(LANGUAGE_CODE='en'):
                            self.assertEqual(
                                form.errors[field],
                                ["This field is required to be printed in the book."]
                            )
                        with override_settings(LANGUAGE_CODE='eo'):
                            self.assertEqual(
                                form.errors[field],
                                ["Tiu ĉi kampo estas deviga por esti printita en la libreto."]
                            )
                assert_content = {
                    'en': "You want to be in the printed edition",
                    'eo': "Vi volas esti en la printita eldonaĵo",
                }
                assert_message = (
                    "Form error does not include clarification about book requirements.\n"
                    "\n\tExpected to see: {!r}"
                    "\n\tBut saw instead: {!r}"
                )
                for lang in assert_content:
                    with override_settings(LANGUAGE_CODE=lang):
                        assert_localized_message = assert_message.format(
                            assert_content[lang], form.errors[NON_FIELD_ERRORS])
                        self.assertTrue(
                            any(
                                assert_content[lang] in error
                                for error in form.errors[NON_FIELD_ERRORS]
                            ),
                            msg=assert_localized_message
                        )
                if "complex" in profile_tag:
                    assert_content = {
                        'en': "You are a host in 3 places, of which 1 should be in the printed edition.",
                        'eo': "Vi estas gastiganto en 3 lokoj, el kiuj 1 estu en la printita eldonaĵo.",
                    }
                    assert_message = "Form error does not include a mention of nr of host's places."
                    for lang in assert_content:
                        with override_settings(LANGUAGE_CODE=lang):
                            self.assertTrue(
                                any(
                                    error == assert_content[lang]
                                    for error in form.errors[NON_FIELD_ERRORS]
                                ),
                                msg=assert_message
                            )

    def test_invalid_birth_date_after_death_date(self):
        # A profile with birth date later than death date is expected to be invalid.
        profile = self.profile_with_no_places_deceased.obj
        form = self._init_form(
            {
                'first_name': "Aa",
                'last_name': "Bb",
                'birth_date': self.faker.date_between(
                    start_date=profile.death_date + timedelta(days=1),
                    end_date=date.today() + timedelta(days=2)
                ),
            },
            instance=profile)
        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors,
                {
                    'birth_date': [
                        "The indicated date of birth is in conflict with the date of death ({:%Y-%m-%d})."
                        .format(profile.death_date)
                    ],
                }
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors,
                {
                    'birth_date': [
                        "La indikita dato de naskiĝo konfliktas kun la dato de forpaso ({:%Y-%m-%d})."
                        .format(profile.death_date)
                    ],
                }
            )

    def test_invalid_birth_date_for_complex_profile(self):
        # A too young profile of a user who wishes to host or meet visitors is expected to be invalid.
        today = date.today()
        try:
            almost_old_enough = today.replace(year=today.year - self.config.host_min_age)
        except ValueError:
            almost_old_enough = today.replace(year=today.year - self.config.host_min_age, day=today.day - 1)
        almost_old_enough += timedelta(days=1)
        error_message = {
            'en': "The minimum age to be allowed hosting is {}.".format(self.config.host_min_age),
            'eo': "Vi ekpovos gastigi kiam estos {}-jaraĝa.".format(self.config.host_min_age),
        }
        hosting_data = (
            self.profile_hosting,
            [self.faker.date_between(start_date='-10y', end_date='-1y'), almost_old_enough],
            error_message)
        host_and_meet_data = (
            self.profile_hosting_and_meeting,
            [self.faker.date_between(start_date='-10y', end_date='-1y'), almost_old_enough],
            error_message)

        try:
            almost_old_enough = today.replace(year=today.year - self.config.meet_min_age)
        except ValueError:
            almost_old_enough = today.replace(year=today.year - self.config.meet_min_age, day=today.day - 1)
        finally:
            almost_old_enough += timedelta(days=1)
        error_message = {
            'en': "The minimum age to be allowed meeting with visitors is {}.".format(self.config.meet_min_age),
            'eo': "Vi ekpovos renkonti vizitantojn kiam estos {}-jaraĝa.".format(self.config.meet_min_age),
        }
        meeting_data = (
            self.profile_meeting,
            [self.faker.date_between(start_date='-10y', end_date='-1y'), almost_old_enough],
            error_message)

        for (profile, profile_tag), dates, assert_content in (hosting_data, meeting_data, host_and_meet_data):
            for birth_date in dates:
                with self.subTest(condition=profile_tag, birth_date=birth_date):
                    form = self._init_form(
                        {
                            'first_name': "Aa",
                            'last_name': "Bb",
                            'birth_date': birth_date,
                        },
                        instance=profile)
                    self.assertFalse(form.is_valid())
                    for lang in assert_content:
                        with override_settings(LANGUAGE_CODE=lang):
                            self.assertEqual(
                                form.errors, {'birth_date': [assert_content[lang]]}
                            )

    def test_invalid_names_for_complex_profile(self):
        # A profile without names of a user who wishes to host or meet visitors is expected to be invalid.
        for profile, profile_tag in (self.profile_hosting,
                                     self.profile_meeting,
                                     self.profile_hosting_and_meeting,
                                     self.profile_in_book,
                                     self.profile_in_book_complex):
            with self.subTest(condition=profile_tag):
                form = self._init_form(
                    {
                        'first_name': "\t  \n " + chr(0xA0),
                        'last_name': " \r  \f\v",
                        'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                        'gender': self.faker.word(),
                    },
                    instance=profile)
                self.assertFalse(form.is_valid())
                if "in book" not in profile_tag:
                    with override_settings(LANGUAGE_CODE='en'):
                        self.assertEqual(
                            form.errors,
                            {
                                NON_FIELD_ERRORS: ["Please indicate how guests should name you"],
                            }
                        )
                    with override_settings(LANGUAGE_CODE='eo'):
                        self.assertEqual(
                            form.errors,
                            {
                                NON_FIELD_ERRORS: ["Bonvole indiku kiel gastoj nomu vin"],
                            }
                        )
                else:
                    with override_settings(LANGUAGE_CODE='en'):
                        self.assertNotIn(
                            "Please indicate how guests should name you",
                            form.errors[NON_FIELD_ERRORS]
                        )
                    with override_settings(LANGUAGE_CODE='eo'):
                        self.assertNotIn(
                            "Bonvole indiku kiel gastoj nomu vin",
                            form.errors[NON_FIELD_ERRORS]
                        )

    @tag('avatar')
    @override_settings(MEDIA_ROOT='tests/assets/')
    def test_missing_avatar_file(self):
        # The form is expected to raise an error when existing avatar file
        # cannot be found on disk.
        profile = ProfileFactory(avatar='null.png')
        form = self._init_form({}, instance=profile, save=True)
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors['avatar'],
                [
                    "There seems to be a problem with the avatar's file. "
                    "Please re-upload it or choose 'Clear'."
                ]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors['avatar'],
                [
                    "Ŝajnas ke estas problemo pri la profilbilda dosiero. "
                    "Bonvole re-alŝutu ĝin aŭ elektu “Vakigi”."
                ]
            )
        self.assertRaises(ValueError, form.save)

    def test_valid_data(self):
        for profile, profile_tag in (self.profile_with_no_places,
                                     self.profile_hosting,
                                     self.profile_meeting,
                                     self.profile_hosting_and_meeting,
                                     self.profile_in_book,
                                     self.profile_in_book_complex):
            super().test_valid_data(profile, profile_tag)

    def test_view_page(self):
        page = self.app.get(
            reverse('profile_update', kwargs={
                'pk': self.profile_with_no_places.obj.pk,
                'slug': self.profile_with_no_places.obj.autoslug}),
            user=self.profile_with_no_places.obj.user,
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], ProfileForm)

    def test_form_submit(self):
        page = self.app.get(
            reverse('profile_update', kwargs={
                'pk': self.profile_with_no_places.obj.pk,
                'slug': self.profile_with_no_places.obj.autoslug}),
            user=self.profile_with_no_places.obj.user,
        )
        page.form['first_name'] = LocaleFaker._get_faker(locale='hu').first_name()
        page.form['last_name'] = LocaleFaker._get_faker(locale='cs').last_name()
        page = page.form.submit()
        self.profile_with_no_places.obj.refresh_from_db()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': self.profile_with_no_places.obj.pk,
                'slug': self.profile_with_no_places.obj.autoslug})
        )


@tag('forms', 'forms-profile', 'profile')
class ProfileCreateFormTests(ProfileFormTestingBase, WebTest):
    def _init_form(self, data=None, files=None, instance=None, empty=False, save=False, user=None):
        if not empty:
            assert instance is not None
        for_user = user or (instance.user if not save else UserFactory(profile=None))
        return ProfileCreateForm(data=data, files=files, user=for_user)

    def test_invalid_init(self):
        # Form without a user associated with the profile is expected to be invalid.
        with self.assertRaises(KeyError) as cm:
            ProfileCreateForm({})
        self.assertEqual(cm.exception.args[0], 'user')

    def test_valid_data(self):
        super().test_valid_data(*self.profile_with_no_places)

    def test_view_page(self):
        page = self.app.get(reverse('profile_create'), user=UserFactory(profile=None))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], ProfileCreateForm)

    def test_form_submit(self):
        user = UserFactory(profile=None)
        page = self.app.get(reverse('profile_create'), user=user)
        page.form['first_name'] = LocaleFaker._get_faker(locale='hu').first_name()
        page.form['last_name'] = LocaleFaker._get_faker(locale='cs').last_name()
        page = page.form.submit()
        user.refresh_from_db()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': user.profile.pk,
                'slug': user.profile.autoslug})
        )
        self.assertEqual(user.profile.email, user.email)


@tag('forms', 'forms-profile', 'profile')
class ProfileEmailUpdateFormTests(EmailUpdateFormTests):
    empty_is_invalid = False

    @classmethod
    def setUpTestData(cls):
        cls.user = ProfileFactory(with_email=True)
        cls.user.username = cls.user.user.username
        cls.invalid_email_user = ProfileFactory(with_email=True, invalid_email=True)
        cls.invalid_email_user.username = cls.invalid_email_user.user.username

    def _init_form(self, data=None, instance=None):
        return ProfileEmailUpdateForm(data=data, instance=instance)

    def test_init(self):
        form = ProfileEmailUpdateForm(instance=self.invalid_email_user)
        # Verify that the expected fields are part of the form.
        self.assertEqual(['email'], list(form.fields))
        # Verify that the form stores the cleaned up email address.
        self.assertEqual(form.initial['email'], self.invalid_email_user._clean_email)
        # Verify the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form.save, 'alters_data')
            or hasattr(form.save, 'do_not_call_in_templates')
        )

    def test_invalid_prefix_email(self):
        # We are not concerned about the invalid prefix for profile email.
        pass

    def test_nonunique_email(self):
        # We are not concerned about non-unique profile emails.
        pass

    def test_view_page(self):
        page = self.app.get(
            reverse('profile_email_update', kwargs={
                'pk': self.invalid_email_user.pk,
                'slug': self.invalid_email_user.autoslug}),
            user=self.invalid_email_user.user,
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], ProfileEmailUpdateForm)

    def form_submission_tests(self, *, lang, obj=None):
        random_email = Faker._get_faker().email(safe=False)
        for new_email in (" ", random_email):
            page = self.app.get(
                reverse('profile_email_update', kwargs={
                    'pk': self.user.pk,
                    'slug': self.user.autoslug}),
                user=self.user.user,
            )
            page.form['email'] = new_email
            page = page.form.submit()
            self.user.refresh_from_db()
            self.assertRedirects(
                page,
                '{}#e{}'.format(
                    reverse('profile_edit', kwargs={
                        'pk': self.user.pk,
                        'slug': self.user.autoslug}),
                    self.user.pk,
                )
            )
            self.assertEqual(self.user.email, new_email.strip())


@tag('forms', 'forms-profile', 'profile')
class PreferenceOptinsFormTests(WebTest):
    def test_init(self):
        form_empty = PreferenceOptinsForm()
        expected_fields = [
            'public_listing',
            'site_analytics_consent',
        ]
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(expected_fields), set(form_empty.fields))

        # Verify that fields are not unnecessarily marked 'required'.
        for field in expected_fields:
            with self.subTest(field=field):
                self.assertFalse(form_empty.fields[field].required)

        # Verify that the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form_empty.save, 'alters_data')
            or hasattr(form_empty.save, 'do_not_call_in_templates')
        )

    def test_view_page(self):
        user = ProfileFactory(user=UserFactory(invalid_email=True))
        page = self.app.get(
            reverse('profile_settings', kwargs={'pk': user.pk, 'slug': user.autoslug}),
            user=user.user,
        )
        self.assertEqual(page.status_code, 200)
        self.assertGreaterEqual(len(page.forms), 1)
        self.assertIn('optinouts_form', page.context)
        self.assertIsInstance(page.context['optinouts_form'], PreferenceOptinsForm)

    def test_form_submit(self):
        user = ProfileFactory(with_email=True)
        page = self.app.get(
            reverse('profile_settings', kwargs={'pk': user.pk, 'slug': user.autoslug}),
            user=user.user,
        )
        self.assertTrue(user.pref.public_listing)
        form = page.forms['privacy_form']
        form['public_listing'] = False
        page = form.submit()
        user.refresh_from_db()
        self.assertRedirects(
            page,
            '{}#pR'.format(
                reverse('profile_edit', kwargs={'pk': user.pk, 'slug': user.autoslug})
            )
        )
        self.assertFalse(user.pref.public_listing)
        self.assertTrue(user.pref.site_analytics_consent)
