from django.test import override_settings, tag
from django.urls import reverse
from django.utils.timezone import make_aware

from django_countries import Countries
from django_webtest import WebTest
from factory import Faker

from core.models import SiteConfiguration
from hosting.forms.phones import PhoneCreateForm, PhoneForm
from hosting.models import Phone

from ..factories import LocaleFaker, PhoneFactory, ProfileFactory


@tag('forms', 'forms-phone', 'phone')
class PhoneFormTests(WebTest):
    @classmethod
    def setUpClass(cls):
        cls.faker = Faker._get_faker()
        cls.all_countries = Countries().countries.keys()
        super().setUpClass()
        cls.config = SiteConfiguration.get_solo()
        cls.expected_fields = [
            'country',
            'type',
            'number',
            'comments',
        ]

    @classmethod
    def setUpTestData(cls):
        cls.profile_one = ProfileFactory()
        cls.phone1_valid = PhoneFactory(profile=cls.profile_one)
        cls.phone2_valid = PhoneFactory(profile=cls.profile_one)
        cls.phone3_deleted = PhoneFactory(
            profile=cls.profile_one,
            deleted_on=make_aware(cls.faker.date_time_this_decade()))

        cls.profile_two = ProfileFactory()
        cls.phone4_valid = PhoneFactory(profile=cls.profile_two)
        cls.phone5_deleted = PhoneFactory(
            profile=cls.profile_two,
            deleted_on=make_aware(cls.faker.date_time_this_decade()))

    def _init_form(self, data=None, instance=None, owner=None):
        assert instance is not None
        return PhoneForm(data=data, instance=instance)

    def test_init(self):
        form = self._init_form(instance=self.phone1_valid, owner=self.profile_one)
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(self.expected_fields), set(form.fields))
        # Verify that fields are marked 'required'.
        for field in ('country', 'type', 'number'):
            with self.subTest(field=field):
                self.assertTrue(form.fields[field].required)
        # Verify that the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form.save, 'alters_data')
            or hasattr(form.save, 'do_not_call_in_templates')
        )

    def test_invalid_init(self):
        # Form without a phone instance is expected to be invalid.
        with self.assertRaises(AttributeError) as cm:
            PhoneForm({})
        self.assertEqual(str(cm.exception), "Phone has no profile.")

    def test_blank_data(self):
        # Empty form is expected to be invalid.
        form = self._init_form(data={}, instance=self.phone1_valid, owner=self.profile_one)
        self.assertFalse(form.is_valid())
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors,
                {
                    'country': ["This field is required."],
                    'type': ["This field is required."],
                    'number': ["This field is required."],
                }
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors,
                {
                    'country': ["Ĉi tiu kampo estas deviga."],
                    'type': ["Ĉi tiu kampo estas deviga."],
                    'number': ["Ĉi tiu kampo estas deviga."],
                }
            )

    def test_invalid_country(self):
        form = self._init_form(data={'country': ""}, instance=self.phone2_valid, owner=self.profile_one)
        self.assertFalse(form.is_valid())
        self.assertIn('country', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(form.errors['country'], ["This field is required."])
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(form.errors['country'], ["Ĉi tiu kampo estas deviga."])

        form = self._init_form(data={'country': "ZZ"}, instance=self.phone4_valid, owner=self.profile_two)
        self.assertFalse(form.is_valid())
        self.assertIn('country', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors['country'],
                ["Select a valid choice. ZZ is not one of the available choices."]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors['country'],
                ["Elektu validan elekton. ZZ ne estas el la eblaj elektoj."]
            )

    def test_invalid_number(self):
        form = self._init_form(
            data={
                'country': "PL",
                'type': "m",
                'number': "+31600000001"
            },
            instance=self.phone1_valid,
            owner=self.profile_one)
        self.assertFalse(form.is_valid())
        self.assertIn('number', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(form.errors['number'], ["Enter a valid phone number."])
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(form.errors['number'], ["Bv. enigu ĝustan telefon-numeron."])

    def test_unique_number(self):
        # Resaving the same form without change is expected to be valid.
        form = self._init_form(instance=self.phone1_valid, owner=self.profile_one)
        form = self._init_form(data=form.initial.copy(), instance=self.phone1_valid, owner=self.profile_one)
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        phone = form.save(commit=False)
        self.assertEqual(phone.pk, self.phone1_valid.pk)
        self.assertEqual(phone.number, self.phone1_valid.number)

        # Resaving the same form with change in non-number related fields is expected to be valid.
        data = form.initial.copy()
        data['country'] = self.faker.random_element(elements=set(self.all_countries) - set([data['country']]))
        data['type'] = self.faker.random_element(elements=Phone.PhoneType.values)
        form = self._init_form(data=data, instance=self.phone1_valid, owner=self.profile_one)
        self.assertTrue(form.is_valid())
        phone = form.save(commit=False)
        self.assertEqual(phone.pk, self.phone1_valid.pk)
        self.assertEqual(phone.number, self.phone1_valid.number)
        self.assertEqual(phone.country, self.phone1_valid.country)

        # Resaving the same form with change in only the number field is expected to be valid.
        data['number'] = PhoneFactory.number.evaluate(self.phone1_valid, None, None)
        form = self._init_form(data=data, instance=self.phone1_valid, owner=self.profile_one)
        self.assertTrue(form.is_valid())
        phone = form.save(commit=False)
        self.assertEqual(phone.pk, self.phone1_valid.pk)
        self.assertEqual(phone.number, self.phone1_valid.number)

        # A phone form with number belonging to a different user is expected to be valid.
        data['number'] = self.phone4_valid.number
        form = self._init_form(data=data, instance=self.phone1_valid, owner=self.profile_one)
        self.assertTrue(form.is_valid())
        phone = form.save(commit=False)
        self.assertEqual(phone.pk, self.phone1_valid.pk)
        self.assertNotEqual(phone.pk, self.phone4_valid.pk)
        self.assertEqual(phone.number, self.phone1_valid.number)
        self.assertFalse(phone.deleted_on)

        data['number'] = self.phone5_deleted.number
        form = self._init_form(data=data, instance=self.phone1_valid, owner=self.profile_one)
        self.assertTrue(form.is_valid())
        phone = form.save(commit=False)
        self.assertEqual(phone.pk, self.phone1_valid.pk)
        self.assertNotEqual(phone.pk, self.phone5_deleted.pk)
        self.assertEqual(phone.number, self.phone1_valid.number)
        self.assertFalse(phone.deleted_on)

    def test_non_unique_number(self):
        # A phone form with active number belonging to the same user is expected to be invalid,
        # and belonging to a different user is expected to be valid.
        # A phone form with inactive number belonging to the same user is expected to be valid,
        phone6_deleted = PhoneFactory(
            profile=self.profile_one,
            deleted_on=make_aware(self.faker.date_time_this_decade()))
        phone6_deleted.set_check_status(self.profile_two.user)
        test_data = [
            ("same user/active", self.phone1_valid, False),
            ("same user/active", self.phone2_valid, False),
            ("same user/deleted", phone6_deleted, True),  # A side-effect is expected. It shouldn't affect other tests.
            ("other user/active", self.phone4_valid, True),
            ("other user/deleted", self.phone5_deleted, True),
        ]

        for case_tag, other_phone, expected_valid in test_data:
            initial_phone = PhoneFactory(profile=self.profile_one)
            remaining_countries = set(self.all_countries) - set([initial_phone.country.code])
            with self.subTest(tag=case_tag):
                form_data = {
                    'country': self.faker.random_element(elements=remaining_countries),
                    'type': self.faker.random_element(elements=Phone.PhoneType.values),
                    'number': other_phone.number,
                    'comments': self.faker.sentence(),
                }
                form = self._init_form(data=form_data, instance=initial_phone, owner=self.profile_one)

                self.assertEqual(form.is_valid(), expected_valid)
                if not expected_valid:
                    self.assertIn('number', form.errors)
                    with override_settings(LANGUAGE_CODE='en'):
                        self.assertEqual(
                            form.errors,
                            {'number': ["You already have this telephone number."]}
                        )
                    with override_settings(LANGUAGE_CODE='eo'):
                        self.assertEqual(
                            form.errors,
                            {'number': ["Vi jam indikis tian telefonnumeron."]}
                        )
                else:
                    phone = form.save()
                    initial_phone.refresh_from_db()
                    for field_name in self.expected_fields:
                        self.assertEqual(getattr(phone, field_name), form_data[field_name])
                    self.assertIsNone(phone.deleted_on)
                    self.assertIsNone(phone.checked_on)
                    self.assertIsNone(phone.checked_by)
                    self.assertEqual(phone.profile_id, initial_phone.profile_id)
                    if case_tag == "same user/deleted":
                        self.assertEqual(phone.pk, other_phone.pk)
                        if type(form) is PhoneForm:
                            self.assertIsNotNone(initial_phone.deleted_on)
                    else:
                        self.assertNotEqual(phone.pk, other_phone.pk)

    def test_view_page(self):
        page = self.app.get(
            reverse('phone_update', kwargs={
                'pk': self.phone1_valid.pk,
                'profile_pk': self.profile_one.pk}),
            user=self.profile_one.user,
        )
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIs(type(page.context['form']), PhoneForm)

    def test_form_submit(self):
        page = self.app.get(
            reverse('phone_update', kwargs={
                'pk': self.phone4_valid.pk,
                'profile_pk': self.profile_two.pk}),
            user=self.profile_two.user,
        )
        page.form['comments'] = comment = (
            LocaleFaker._get_faker(locale='ar').text(max_nb_chars=250)
        )
        page = page.form.submit()
        self.phone4_valid.refresh_from_db()
        self.assertRedirects(
            page,
            '{}#t{}'.format(
                reverse('profile_edit', kwargs={
                    'pk': self.profile_two.pk,
                    'slug': self.profile_two.autoslug}),
                self.phone4_valid.pk,
            )
        )
        self.assertEqual(self.phone4_valid.comments, comment.rstrip())


class PhoneCreateFormTests(PhoneFormTests):
    def _init_form(self, data=None, instance=None, owner=None):
        assert owner is not None
        return PhoneCreateForm(data=data, profile=owner)

    def test_invalid_init(self):
        # Form without a future phone's owner is expected to be invalid.
        with self.assertRaises(KeyError) as cm:
            PhoneCreateForm({})
        self.assertEqual(str(cm.exception), "'profile'")

    def test_unique_number(self):
        # Form with number not appearing anywhere else is expected to be valid.
        form_data = {
            'country': self.faker.random_element(elements=self.all_countries),
            'type': self.faker.random_element(elements=Phone.PhoneType.values),
            'number': PhoneFactory.number.evaluate(None, None, None),
            'comments': self.faker.sentence(),
        }
        form = self._init_form(data=form_data, owner=ProfileFactory())
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        phone = form.save(commit=False)
        for field_name in form_data:
            self.assertEqual(getattr(phone, field_name), form_data[field_name])

    def test_view_page(self):
        page = self.app.get(
            reverse('phone_create', kwargs={'profile_pk': self.profile_one.pk}),
            user=self.profile_one.user,
        )
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIs(type(page.context['form']), PhoneCreateForm)

    def test_form_submit(self):
        page = self.app.get(
            reverse('phone_create', kwargs={'profile_pk': self.profile_two.pk}),
            user=self.profile_two.user,
        )
        page.form['country'] = self.faker.random_element(elements=self.all_countries)
        page.form['type'] = self.faker.random_element(elements=Phone.PhoneType.values)
        number = PhoneFactory.number.evaluate(None, None, None)
        page.form['number'] = number.as_international
        page.form['comments'] = comment = (
            LocaleFaker._get_faker(locale='th').text(max_nb_chars=250)
        )
        page = page.form.submit()
        new_phone = Phone.all_objects.filter(profile=self.profile_two).order_by('-id').first()
        self.assertRedirects(
            page,
            '{}#t{}'.format(
                reverse('profile_edit', kwargs={
                    'pk': self.profile_two.pk,
                    'slug': self.profile_two.autoslug}),
                new_phone.pk,
            )
        )
        self.assertEqual(new_phone.number, number)
        self.assertEqual(new_phone.comments, comment.rstrip())
