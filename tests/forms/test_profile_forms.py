from collections import namedtuple
from datetime import date, timedelta

from django.core.exceptions import NON_FIELD_ERRORS
from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest
from factory import Faker as FakerFactory
from faker import Faker

from core.models import SiteConfiguration
from hosting.forms.profiles import ProfileForm
from hosting.models import MR, MRS, PRONOUN_CHOICES

from ..factories import PlaceFactory, ProfileFactory


@tag('forms', 'forms-profile', 'profile')
@override_settings(LANGUAGE_CODE='en')
class ProfileFormTests(WebTest):
    @classmethod
    def setUpTestData(cls):
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
        cls.faker = Faker()
        TaggedProfile = namedtuple('TaggedProfile', 'obj, tag')

        cls.profile_with_no_places = TaggedProfile(ProfileFactory(), "simple")
        cls.profile_with_no_places_deceased = TaggedProfile(ProfileFactory(deceased=True), "deceased")

        profile = ProfileFactory()
        cls.profile_hosting = TaggedProfile(profile, "hosting")
        PlaceFactory(owner=profile, available=True)

        profile = ProfileFactory()
        cls.profile_meeting = TaggedProfile(profile, "meeting")
        PlaceFactory(owner=profile, available=False, have_a_drink=True)

        profile = ProfileFactory()
        cls.profile_hosting_and_meeting = TaggedProfile(profile, "hosting & meeting")
        PlaceFactory(owner=profile, available=True)
        PlaceFactory(owner=profile, available=False, tour_guide=True)

        profile = ProfileFactory()
        cls.profile_in_book = TaggedProfile(profile, "in book (simple)")
        PlaceFactory(owner=profile, available=True, in_book=True)

        profile = ProfileFactory()
        cls.profile_in_book_complex = TaggedProfile(profile, "in book (complex)")
        PlaceFactory(owner=profile, available=True, in_book=True)
        PlaceFactory(owner=profile, available=True, in_book=False)
        PlaceFactory(owner=profile, available=False, have_a_drink=True, in_book=False)

    def setUp(self):
        self.profile_with_no_places.obj.refresh_from_db()
        self.profile_with_no_places_deceased.obj.refresh_from_db()
        self.profile_hosting.obj.refresh_from_db()
        self.profile_meeting.obj.refresh_from_db()
        self.profile_hosting_and_meeting.obj.refresh_from_db()
        self.profile_in_book.obj.refresh_from_db()
        self.profile_in_book_complex.obj.refresh_from_db()

    def test_init(self):
        form_empty = ProfileForm()
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
        self.assertEquals(set(expected_fields), set(form_empty.fields))

        # Verify that fields are not unnecessarily marked 'required'.
        for form in (form_empty, ProfileForm(instance=self.profile_with_no_places.obj)):
            for field in set(self.host_required_fields) | set(self.book_required_fields):
                with self.subTest(field=field):
                    self.assertFalse(form.fields[field].required)

        # Verify that fields are marked 'required' when user is hosting or meeting.
        for form, profile_tag in ([ProfileForm(instance=self.profile_hosting.obj),
                                   self.profile_hosting.tag],
                                  [ProfileForm(instance=self.profile_meeting.obj),
                                   self.profile_meeting.tag],
                                  [ProfileForm(instance=self.profile_hosting_and_meeting.obj),
                                   self.profile_hosting_and_meeting.tag]):
            for field in self.host_required_fields:
                with self.subTest(condition=profile_tag, field=field):
                    self.assertTrue(form.fields[field].required)

        # Verify that fields are marked 'required' when user is in the printed edition.
        for form, profile_tag in ([ProfileForm(instance=self.profile_in_book.obj),
                                   self.profile_in_book.tag],
                                  [ProfileForm(instance=self.profile_in_book_complex.obj),
                                   self.profile_in_book_complex.tag]):
            for field in self.book_required_fields:
                with self.subTest(condition=profile_tag, field=field):
                    self.assertTrue(form.fields[field].required)

        # Verify that the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form_empty.save, 'alters_data')
            or hasattr(form_empty.save, 'do_not_call_in_templates')
        )

    def test_blank_data(self):
        # Empty form is expected to be valid.
        form = ProfileForm({})
        self.assertTrue(form.is_valid())

        # Empty form for simple profile is expected to be valid.
        form = ProfileForm({}, instance=self.profile_with_no_places.obj)
        self.assertTrue(form.is_valid())

        # Empty form for complex profile (hosting or meeting or in book) is expected to be invalid.
        for form, profile_tag in ([ProfileForm({}, instance=self.profile_hosting.obj),
                                   self.profile_hosting.tag],
                                  [ProfileForm({}, instance=self.profile_meeting.obj),
                                   self.profile_meeting.tag],
                                  [ProfileForm({}, instance=self.profile_hosting_and_meeting.obj),
                                   self.profile_hosting_and_meeting.tag]):
            with self.subTest(condition=profile_tag):
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors, {
                    NON_FIELD_ERRORS: ["Please indicate how guests should name you"],
                    'birth_date': ["This field is required."],
                })
        for form, profile_tag in ([ProfileForm({}, instance=self.profile_in_book.obj),
                                   self.profile_in_book.tag],
                                  [ProfileForm({}, instance=self.profile_in_book_complex.obj),
                                   self.profile_in_book_complex.tag]):
            with self.subTest(condition=profile_tag):
                self.assertFalse(form.is_valid())
                self.assertEqual(set(form.errors.keys()), set(self.book_required_fields + [NON_FIELD_ERRORS]))
                for field in self.book_required_fields:
                    with self.subTest(field=field):
                        self.assertEqual(
                            form.errors[field],
                            ["This field is required to be printed in the book."]
                        )
                assert_content = "You want to be in the printed edition"
                assert_message = (
                    "Form error does not include clarification about book requirements.\n"
                    f"\n\tExpected to see: {assert_content}"
                    f"\n\tBut saw instead: {form.errors[NON_FIELD_ERRORS]!r}"
                )
                self.assertTrue(
                    any(assert_content in error for error in form.errors[NON_FIELD_ERRORS]), msg=assert_message
                )
                if "complex" in profile_tag:
                    assert_content = "You are a host in 3 places, of which 1 should be in the printed edition."
                    assert_message = "Form error does not include a mention of nr of host's places."
                    self.assertTrue(
                        any(error == assert_content for error in form.errors[NON_FIELD_ERRORS]), msg=assert_message
                    )

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
                    form = ProfileForm(
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
                        if profile_tag == "simple":
                            self.assertEqual(form.errors, {
                                'birth_date': ["Ensure this value is less than or equal to {}.".format(today)],
                            })
                        elif profile_tag == "deceased":
                            self.assertEqual(form.errors, {
                                'birth_date': ["The indicated date of birth is in conflict with the date of death"
                                               " ({:%Y-%m-%d}).".format(profile.death_date)],
                            })
                        else:
                            self.assertTrue(any(err.startswith("The minimum age to be allowed ")
                                                for err in form.errors['birth_date']),
                                            msg="Form field 'birth_date' error does not indicate minimum age.")
                    if violation_type == "too dead":
                        self.assertEqual(form.errors, {
                            'birth_date': ["Ensure this value is greater than or equal to {}.".format(max_past)],
                        })

    def test_invalid_birth_date_after_death_date(self):
        # A profile with birth date later than death date is expected to be invalid.
        profile = self.profile_with_no_places_deceased.obj
        form = ProfileForm(
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
        self.assertEqual(form.errors, {
            'birth_date': ["The indicated date of birth is in conflict with the date of death ({:%Y-%m-%d})."
                           .format(profile.death_date)],
        })

    def test_invalid_birth_date_for_complex_profile(self):
        # A too young profile of a user who wishes to host or meet visitors is expected to be invalid.
        today = date.today()
        try:
            almost_old_enough = today.replace(year=today.year - self.config.host_min_age)
        except ValueError:
            almost_old_enough = today.replace(year=today.year - self.config.host_min_age, day=today.day - 1)
        finally:
            almost_old_enough += timedelta(days=1)
        error_message = "The minimum age to be allowed hosting is {}.".format(self.config.host_min_age)
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
        error_message = "The minimum age to be allowed meeting with visitors is {}.".format(self.config.meet_min_age)
        meeting_data = (
            self.profile_meeting,
            [self.faker.date_between(start_date='-10y', end_date='-1y'), almost_old_enough],
            error_message)

        for (profile, profile_tag), dates, assert_content in (hosting_data, meeting_data, host_and_meet_data):
            for birth_date in dates:
                with self.subTest(condition=profile_tag, birth_date=birth_date):
                    form = ProfileForm(
                        {
                            'first_name': "Aa",
                            'last_name': "Bb",
                            'birth_date': birth_date,
                        },
                        instance=profile)
                    self.assertFalse(form.is_valid())
                    self.assertEqual(form.errors, {
                        'birth_date': [assert_content],
                    })

    def test_valid_birth_date(self):
        # A very young profile of a user who neither hosts nor meets visitors is expected to be valid.
        form = ProfileForm(
            {
                'first_name': "Aa",
                'last_name': "Bb",
                'birth_date': self.faker.date_between(start_date='-16y', end_date=date.today()),
            },
            instance=self.profile_with_no_places.obj)
        self.assertTrue(form.is_valid())

        # A young profile of a deceased user who neither hosted nor met visitors is expected to be valid.
        form = ProfileForm(
            {
                'first_name': "Aa",
                'last_name': "Bb",
                'birth_date': self.faker.date_between(start_date='-22y', end_date='-11y'),
            },
            instance=self.profile_with_no_places_deceased.obj)
        self.assertTrue(form.is_valid())

    def test_invalid_names(self):
        # A profile with names containing non-latin characters or digits is expected to be invalid.
        test_data = (
            ("latin name",
             FakerFactory('name', locale='zh'),
             "provide this data in Latin characters"),
            ("symbols",
             FakerFactory('password', upper_case=False, lower_case=False, digits=False, special_chars=True),
             "provide this data in Latin characters"),
            ("digits",
             FakerFactory('password', upper_case=False, lower_case=True, digits=True, special_chars=False),
             "Digits are not allowed"),
            ("all caps",
             FakerFactory('password', upper_case=True, lower_case=False, digits=False, special_chars=False),
             "Today is not CapsLock day"),
            ("many caps", "AaAaAaAaA", "there are too many uppercase letters"),
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
                            'first_name': Faker(locale='id').first_name(),
                            'last_name': Faker(locale='tr').last_name(),
                            'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                            'gender': self.faker.word(),
                        }
                        data[wrong_field] = (
                            field_value.generate({}) if isinstance(field_value, FakerFactory) else field_value
                        )
                        with self.subTest(value=data[wrong_field]):
                            form = ProfileForm(data, instance=profile)
                            self.assertFalse(form.is_valid())
                            self.assertIn(wrong_field, form.errors)
                            self.assertTrue(any(assert_content in error for error in form.errors[wrong_field]))

    def test_invalid_names_for_complex_profile(self):
        # A profile without names of a user who wishes to host or meet visitors is expected to be invalid.
        for profile, profile_tag in (self.profile_hosting,
                                     self.profile_meeting,
                                     self.profile_hosting_and_meeting,
                                     self.profile_in_book,
                                     self.profile_in_book_complex):
            with self.subTest(condition=profile_tag):
                form = ProfileForm(
                    {
                        'first_name': "\t  \n " + chr(0xA0),
                        'last_name': " \r  \f\v",
                        'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                        'gender': self.faker.word(),
                    },
                    instance=profile)
                self.assertFalse(form.is_valid())
                if "in book" not in profile_tag:
                    self.assertEqual(form.errors, {
                        NON_FIELD_ERRORS: ["Please indicate how guests should name you"],
                    })
                else:
                    self.assertNotIn("Please indicate how guests should name you", form.errors[NON_FIELD_ERRORS])

    def test_valid_names(self):
        # A profile with only one of the names of a user who wishes to host or meet visitors is expected to be valid.
        for profile, profile_tag in (self.profile_hosting,
                                     self.profile_meeting,
                                     self.profile_hosting_and_meeting):
            with self.subTest(condition=profile_tag, name="first name"):
                form = ProfileForm(
                    {
                        'first_name': Faker(locale='en').first_name(),
                        'last_name': "",
                        'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                    },
                    instance=profile)
                self.assertTrue(form.is_valid())
            with self.subTest(condition=profile_tag, name="last name"):
                form = ProfileForm(
                    {
                        'first_name': "",
                        'last_name': Faker(locale='en').last_name(),
                        'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                    },
                    instance=profile)
                self.assertTrue(form.is_valid())

    def test_valid_data_for_simple_profile(self):
        form = ProfileForm({}, instance=self.profile_with_no_places.obj)
        self.assertTrue(form.is_valid())
        profile = form.save()
        self.assertIs(profile, self.profile_with_no_places.obj)
        self.assertEqual(profile.first_name, "")
        self.assertEqual(profile.last_name, "")
        self.assertFalse(profile.names_inversed)
        self.assertEqual(profile.title, "")
        self.assertIsNone(profile.gender)
        self.assertEqual(profile.pronoun, "")
        self.assertIsNone(profile.birth_date)
        self.assertEqual(profile.description, "")

    def test_valid_data(self):
        for dataset_type in ("full", "partial"):
            for profile, profile_tag in (self.profile_with_no_places,
                                         self.profile_hosting,
                                         self.profile_meeting,
                                         self.profile_hosting_and_meeting,
                                         self.profile_in_book,
                                         self.profile_in_book_complex):
                data = {
                    'first_name': Faker(locale='fr').first_name(),
                    'last_name': Faker(locale='es').last_name(),
                    'names_inversed': self.faker.boolean(),
                    'title': self.faker.random_element(elements=[MRS, MR]) if dataset_type == "full" else "",
                    'birth_date': self.faker.date_between(start_date='-100y', end_date='-18y'),
                    'description': self.faker.text() if dataset_type == "full" else "",
                    'gender': self.faker.word() if dataset_type == "full" or "in book" in profile_tag else None,
                    'pronoun': (self.faker.random_element(elements=[ch[0] for ch in PRONOUN_CHOICES])
                                if dataset_type == "full" else None),
                }
                with self.subTest(dataset=dataset_type, condition=profile_tag):
                    form = ProfileForm(data, instance=profile)
                    self.assertTrue(form.is_valid())
                    saved_profile = form.save()
                    self.assertIs(saved_profile, profile)
                    for field in data:
                        with self.subTest(field=field):
                            if field == 'gender':
                                self.assertEqual(getattr(profile, field), data[field])
                            else:
                                self.assertEqual(
                                    getattr(profile, field),
                                    data[field] if data[field] is not None else ""
                                )

    def test_view_page(self):
        page = self.app.get(
            reverse('profile_update', kwargs={
                'pk': self.profile_with_no_places.obj.pk,
                'slug': self.profile_with_no_places.obj.autoslug}),
            user=self.profile_with_no_places.obj.user,
        )
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], ProfileForm)

    def test_form_submit(self):
        page = self.app.get(
            reverse('profile_update', kwargs={
                'pk': self.profile_with_no_places.obj.pk,
                'slug': self.profile_with_no_places.obj.autoslug}),
            user=self.profile_with_no_places.obj.user,
        )
        page.form['first_name'] = Faker(locale='hu').first_name()
        page.form['last_name'] = Faker(locale='cs').last_name()
        page = page.form.submit()
        self.profile_with_no_places.obj.refresh_from_db()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': self.profile_with_no_places.obj.pk,
                'slug': self.profile_with_no_places.obj.autoslug})
        )
