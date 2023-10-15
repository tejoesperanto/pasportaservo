from datetime import date, timedelta

from django.test import override_settings, tag
from django.urls import reverse

import rstr
from django_webtest import WebTest
from factory import Faker

from hosting.forms.familymembers import (
    FamilyMemberCreateForm, FamilyMemberForm,
)
from hosting.models import FamilyMember

from ..factories import LocaleFaker, PlaceFactory, ProfileSansAccountFactory


@tag('forms', 'forms-familymembers', 'family-members')
class FamilyMemberFormTests(WebTest):
    form_class = FamilyMemberForm

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.faker = Faker._get_faker()
        cls.expected_fields = [
            'first_name',
            'last_name',
            'names_inversed',
            'title',
            'birth_date',
        ]

    @classmethod
    def setUpTestData(cls):
        cls.place_with_family = PlaceFactory()
        cls.profile_one = ProfileSansAccountFactory(pronoun="", description="")
        cls.place_with_family.family_members.add(cls.profile_one)
        cls.place_anon_family = PlaceFactory()
        cls.profile_two = ProfileSansAccountFactory(
            first_name="", last_name="", pronoun="", description="")
        cls.place_anon_family.family_members.add(cls.profile_two)

    def _init_form(self, data=None, place=None, member_index=0):
        assert place is not None
        assert member_index < len(place.family_members_cache())
        return self.form_class(
            data=data, instance=place.family_members_cache()[member_index], place=place)

    def test_init(self):
        len(self.place_with_family.family_members_cache())  # Force populating cache.
        with self.assertNumQueries(0):
            form = self._init_form(place=self.place_with_family)
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(self.expected_fields), set(form.fields))
        # Verify that fields are not marked 'required'.
        for field in self.expected_fields:
            with self.subTest(field=field):
                self.assertFalse(form.fields[field].required)
        # Help text for 'regular' family is expected to be empty.
        self.assertEqual(form.fields['first_name'].help_text, "")
        self.assertEqual(form.fields['last_name'].help_text, "")
        # Help text for 'anonymous' family is expected to be non-empty.
        len(self.place_anon_family.family_members_cache())  # Force populating cache.
        with self.assertNumQueries(0):
            form = self._init_form(place=self.place_anon_family)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.fields['first_name'].help_text,
                "Leave empty if you only want to indicate that "
                "other people are present in the house."
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.fields['first_name'].help_text,
                "Lasu malplena se vi nure volas indiki ke kromaj "
                "homoj ĉeestas en la loĝejo."
            )
        # Verify that the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form.save, 'alters_data')
            or hasattr(form.save, 'do_not_call_in_templates')
        )

    def test_invalid_init(self):
        # Form without an associated place is expected to be invalid.
        with self.assertRaises(KeyError) as cm:
            self.form_class({})
        self.assertEqual(cm.exception.args[0], 'place')

    def test_blank_data_for_regular_small_family(self):
        # Empty form for member of place's 'regular' 1-person family is expected to be invalid.
        with self.assertNumQueries(1):
            form = self._init_form(data={}, place=self.place_with_family)
            self.assertFalse(form.is_valid())
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.non_field_errors(),
                [
                    "The name cannot be empty, at least first name "
                    "or last name are required."
                ]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.non_field_errors(),
                [
                    "Nomo ne povas esti nenia, almenaŭ unu el "
                    "persona aŭ familia nomoj devas esti indikita."
                ]
            )

    def test_blank_data_for_regular_big_family(self):
        # Empty form for member of place's 'regular' 2-person family is expected to be invalid.
        place_with_big_family = PlaceFactory()
        place_with_big_family.family_members.add(self.profile_one)
        place_with_big_family.family_members.add(ProfileSansAccountFactory())
        with self.assertNumQueries(1):
            form = self._init_form(data={}, place=place_with_big_family, member_index=0)
            self.assertFalse(form.is_valid())
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.non_field_errors(),
                [
                    "The name cannot be empty, at least first name "
                    "or last name are required."
                ]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.non_field_errors(),
                [
                    "Nomo ne povas esti nenia, almenaŭ unu el "
                    "persona aŭ familia nomoj devas esti indikita."
                ]
            )

    def test_blank_data_for_anonymous_family(self):
        # Empty form for member of place's 'anonymous' family is expected to be valid.
        len(self.place_anon_family.family_members_cache())  # Force populating cache.
        with self.assertNumQueries(0):
            form = self._init_form(data={}, place=self.place_anon_family)
            self.assertTrue(form.is_valid(), msg=repr(form.errors))

    def test_invalid_birth_date_in_past(self):
        # An overly young (born in future) or a too old profile is expected to be invalid.
        today = date.today()
        try:
            max_past = today.replace(year=today.year - 200)
        except ValueError:
            max_past = today.replace(year=today.year - 200, day=today.day - 1)
        birth_date = max_past - timedelta(days=1)
        form = self._init_form(
            {
                'first_name': self.faker.first_name(),
                'last_name': self.faker.last_name(),
                'birth_date': birth_date,
            },
            place=self.place_with_family)
        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors,
                {
                    'birth_date': [
                        f"Ensure this value is greater than or equal to {max_past}."
                    ],
                }
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors,
                {
                    'birth_date': [
                        f"Certigu ke ĉi tiu valoro estas pli ol aŭ egala al {max_past}."
                    ],
                }
            )

    def test_invalid_birth_date_in_future(self):
        # An overly young (born in future) family member is expected to be invalid.
        today = date.today()
        birth_date = today + timedelta(days=1)
        form = self._init_form(
            {
                'first_name': self.faker.first_name(),
                'last_name': self.faker.last_name(),
                'birth_date': birth_date,
            },
            place=self.place_with_family)
        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors,
                {
                    'birth_date': [
                        "A family member cannot be future-born (even if planned)."
                    ],
                }
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors,
                {
                    'birth_date': [
                        "Kunloĝanto ne povas naskiĝi estontece, eĉ se planita."
                    ],
                }
            )

    def test_valid_birth_date(self):
        # A family member of any reasonable age is expected to be valid.
        form = self._init_form(
            {
                'first_name': "Aaa",
                'last_name': "Bbb",
                'birth_date': self.faker.date_between(start_date='-99y', end_date=date.today()),
            },
            place=self.place_anon_family)
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        # A family member without a known age is expected to be valid.
        form = self._init_form(
            {
                'first_name': "Ccc",
                'last_name': "Ddd",
            },
            place=self.place_anon_family)
        self.assertTrue(form.is_valid(), msg=repr(form.errors))

    def test_invalid_names(self):
        # A family member with names containing non-latin characters or digits
        # is expected to be invalid.
        ja_faker = LocaleFaker._get_faker(locale='ja')
        test_data = (
            (
                "latin name",
                lambda: ja_faker.name(),
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
            ),
        )

        for field_violation, field_value, assert_content in test_data:
            for wrong_field in ('first_name', 'last_name'):
                with self.subTest(field=wrong_field, violation=field_violation):
                    data = {
                        wrong_field: field_value()
                    }
                    with self.subTest(value=data[wrong_field]):
                        form = self._init_form(data, place=self.place_with_family)
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
        # A family member with only a first name or a last name is expected to be valid.
        with self.subTest(name="first name"):
            form = self._init_form(
                {
                    'first_name': LocaleFaker._get_faker(locale='lt').first_name(),
                    'last_name': "",
                },
                place=self.place_anon_family)
            self.assertTrue(form.is_valid())
        with self.subTest(name="last name"):
            form = self._init_form(
                {
                    'first_name': "",
                    'last_name': LocaleFaker._get_faker(locale='lv').last_name(),
                },
                place=self.place_anon_family)
            self.assertTrue(form.is_valid())

    def test_invalid_title(self):
        # A family member with an unrecognised title is expected to be invalid.
        form = self._init_form(
            {
                'first_name': "Eee",
                'last_name': "Ggg",
                'title': "XYZ",
            },
            place=self.place_with_family)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors,
                {
                    'title': [
                        "Select a valid choice. XYZ is not one of the available choices."
                    ],
                }
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors,
                {
                    'title': [
                        "Elektu validan elekton. XYZ ne estas el la eblaj elektoj."
                    ],
                }
            )

    def test_valid_data(self, for_place=None):
        data = {
            'first_name': LocaleFaker._get_faker(locale='lt').first_name(),
            'last_name': LocaleFaker._get_faker(locale='lv').last_name(),
            'names_inversed': True,
            'birth_date':
                self.faker.date_between(start_date='-99y', end_date=date.today()),
            'title':
                self.faker.random_element(elements=filter(None, FamilyMember.Titles.values)),
        }
        place = for_place or self.place_with_family
        form = self._init_form(data, place=place)
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        profile = form.save(commit=False)
        if type(form) is FamilyMemberForm:
            self.assertEqual(profile.pk, self.profile_one.pk)
        elif type(form) is FamilyMemberCreateForm:
            self.assertNotEqual(profile.pk, self.profile_one.pk)
        self.assertEqual(len(place.family_members.all()), 1)
        self.assertEqual(profile.first_name, data['first_name'])
        self.assertEqual(profile.last_name, data['last_name'])
        self.assertTrue(profile.names_inversed)
        self.assertEqual(profile.title, data['title'])
        self.assertIsNone(profile.gender)
        self.assertEqual(profile.pronoun, "")
        self.assertEqual(profile.birth_date, data['birth_date'])
        self.assertEqual(profile.description, "")

    def test_view_page(self):
        page = self.app.get(
            reverse('family_member_update', kwargs={
                'pk': self.profile_one.pk,
                'place_pk': self.place_with_family.pk}),
            user=self.place_with_family.owner.user,
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIs(type(page.context['form']), self.form_class)

    def test_form_submit(self):
        page = self.app.get(
            reverse('family_member_update', kwargs={
                'pk': self.profile_one.pk,
                'place_pk': self.place_with_family.pk}),
            user=self.place_with_family.owner.user,
        )
        page.form['first_name'] = fname = LocaleFaker._get_faker(locale='et').first_name()
        page.form['last_name'] = lname = LocaleFaker._get_faker(locale='fi').last_name()
        page = page.form.submit()
        self.profile_one.refresh_from_db()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': self.place_with_family.owner.pk,
                'slug': self.place_with_family.owner.autoslug})
        )
        self.assertEqual(self.profile_one.first_name, fname)
        self.assertEqual(self.profile_one.last_name, lname)


class FamilyMemberCreateFormTests(FamilyMemberFormTests):
    form_class = FamilyMemberCreateForm

    def _init_form(self, data=None, place=None, member_index=0):
        assert place is not None
        return self.form_class(data=data, place=place)

    def test_blank_data_for_no_family(self):
        # Empty form for first member of place's family is expected to be valid.
        place_no_family = PlaceFactory()
        with self.assertNumQueries(1):
            form = self._init_form(data={}, place=place_no_family)
            self.assertTrue(form.is_valid(), msg=repr(form.errors))

    def test_valid_data(self, for_place=None):
        super().test_valid_data(for_place or PlaceFactory())

    def test_view_page(self):
        page = self.app.get(
            reverse('family_member_create', kwargs={
                'place_pk': self.place_with_family.pk}),
            user=self.place_with_family.owner.user,
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIs(type(page.context['form']), self.form_class)

    def test_form_submit(self):
        place_with_family = PlaceFactory()
        profile_old = ProfileSansAccountFactory()
        place_with_family.family_members.add(profile_old)

        page = self.app.get(
            reverse('family_member_create', kwargs={
                'place_pk': place_with_family.pk}),
            user=place_with_family.owner.user,
        )
        page.form['first_name'] = fname = LocaleFaker._get_faker(locale='et').first_name()
        page.form['last_name'] = lname = LocaleFaker._get_faker(locale='fi').last_name()
        page.form['title'] = FamilyMember.Titles.MR
        page = page.form.submit()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': place_with_family.owner.pk,
                'slug': place_with_family.owner.autoslug})
        )

        profile_new = place_with_family.family_members.last()
        self.assertNotEqual(profile_old.pk, profile_new.pk)
        self.assertEqual(profile_new.first_name, fname)
        self.assertEqual(profile_new.last_name, lname)
        self.assertEqual(profile_new.birth_date, None)
        self.assertEqual(profile_new.title, FamilyMember.Titles.MR)

    def test_form_submit_anonymous_family(self):
        place_no_family = PlaceFactory()

        page = self.app.get(
            reverse('family_member_create', kwargs={
                'place_pk': place_no_family.pk}),
            user=place_no_family.owner.user,
        )
        page.form['title'] = FamilyMember.Titles.MRS
        page = page.form.submit()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': place_no_family.owner.pk,
                'slug': place_no_family.owner.autoslug})
        )

        family = place_no_family.family_members.all()
        self.assertEqual(len(family), 1)
        self.assertEqual(family[0].first_name, "")
        self.assertEqual(family[0].last_name, "")
        self.assertEqual(family[0].birth_date, None)
        self.assertEqual(family[0].title, FamilyMember.Titles.MRS)
