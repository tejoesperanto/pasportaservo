from django.forms import modelformset_factory
from django.forms.fields import BoundField
from django.test import TestCase, override_settings, tag
from django.utils.timezone import now

from hosting.forms.visibility import VisibilityForm, VisibilityFormSetBase
from hosting.models import Phone, Place, VisibilitySettings

from ..assertions import AdditionalAsserts
from ..factories import (
    PhoneFactory, PlaceFactory, ProfileFactory, ProfileSansAccountFactory,
)


@tag('forms')
class VisibilityFormTests(AdditionalAsserts, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expected_fields = [
            'visible_online_public', 'visible_online_authed', 'visible_in_book',
            'hint', 'indent',
        ]

    @classmethod
    def setUpTestData(cls):
        cls.place = PlaceFactory(in_book=False)
        cls.place.visibility.refresh_from_db()
        cls.place.family_members_visibility.refresh_from_db()
        cls.phone = PhoneFactory(profile=cls.place.profile)
        cls.phone.visibility.refresh_from_db()
        cls.place.profile.email_visibility.refresh_from_db()

    def test_init_normal(self):
        test_dataset = [
            {'obj': self.phone.visibility, 'mod': True},
            {'obj': self.place.visibility, 'mod': False, 'tied_online': True},
            {'obj': self.place.family_members_visibility, 'mod': False},
        ]

        for test_data in test_dataset:
            with self.subTest(type=test_data['obj'].model_type):
                form = VisibilityForm(instance=test_data['obj'])
                # Verify that the expected fields are part of the form.
                self.assertEqual(set(self.expected_fields), set(form.fields))
                # Verify that fields are not marked 'required'.
                for field in self.expected_fields:
                    with self.subTest(field=field):
                        self.assertFalse(form.fields[field].required)
                # Verify that fields are properly marked 'disabled'.
                self.assertFalse(form.fields['visible_online_public'].disabled)
                self.assertEqual(test_data['obj'].rules['online_authed'], test_data['mod'])
                self.assertEqual(form.fields['visible_online_authed'].disabled, not test_data['mod'])
                self.assertTrue(form.fields['hint'].disabled)
                self.assertTrue(form.fields['indent'].disabled)
                # Verify that 'online-public' and 'online-authed' are tied on
                # the client side, when needed.
                self.assertEqual(
                    form.fields['visible_online_public'].widget.attrs.get('data-tied'),
                    str(test_data.get('tied_online', False))
                )
                self.assertEqual(
                    form.fields['visible_online_authed'].widget.attrs.get('data-tied'),
                    str(test_data.get('tied_online', False))
                )
                # Verify that the form's save method is protected in templates.
                self.assertTrue(
                    hasattr(form.save, 'alters_data')
                    or hasattr(form.save, 'do_not_call_in_templates')
                )

    def test_init_readonly(self):
        form = VisibilityForm(instance=self.phone.visibility, read_only=True)
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(self.expected_fields), set(form.fields))
        # Verify that all fields are marked 'disabled'.
        for field in self.expected_fields:
            with self.subTest(field=field):
                self.assertTrue(form.fields[field].disabled)

    def test_inbook_field_disabled(self):
        # Case 1. available: N, in book: N.
        with self.subTest(case=1, available=False, in_book=False):
            place = PlaceFactory(available=False, in_book=False)
            place.visibility.refresh_from_db()
            phone = PhoneFactory(profile=place.profile)
            phone.visibility.refresh_from_db()
            # The `in_book` field for place's visibility object is expected to be disabled.
            form = VisibilityForm(instance=place.visibility)
            self.assertTrue(form.fields['visible_in_book'].disabled)
            # The `in_book` field for phone's visibility object is expected to be disabled.
            form = VisibilityForm(instance=phone.visibility)
            self.assertTrue(form.fields['visible_in_book'].disabled)

        # Case 2. available: Y, in book: N.
        with self.subTest(case=2, available=True, in_book=False):
            self.assertTrue(self.place.available)
            self.assertFalse(self.place.in_book)
            # The `in_book` field for place's visibility object is expected to be disabled.
            form = VisibilityForm(instance=self.place.visibility)
            self.assertTrue(form.fields['visible_in_book'].disabled)
            # The `in_book` field for phone's visibility object is expected to be enabled.
            form = VisibilityForm(instance=self.phone.visibility)
            self.assertFalse(form.fields['visible_in_book'].disabled)

        # Case 3. available: N, in book: Y.
        with self.subTest(case=3, available=False, in_book=True):
            Place.all_objects.filter(pk=place.pk).update(available=False, in_book=True)
            place = Place.all_objects.get(pk=place.pk)
            phone = Phone.all_objects.get(pk=phone.pk)
            # The `in_book` field for place's visibility object is expected to be disabled.
            form = VisibilityForm(instance=place.visibility)
            self.assertTrue(form.fields['visible_in_book'].disabled)
            # The `in_book` field for phone's visibility object is expected to be disabled.
            form = VisibilityForm(instance=phone.visibility)
            self.assertTrue(form.fields['visible_in_book'].disabled)

        # Case 4. available: Y, in book: Y.
        with self.subTest(case=4, available=True, in_book=True):
            Place.all_objects.filter(pk=place.pk).update(available=True, in_book=True)
            place = Place.all_objects.get(pk=place.pk)
            phone = Phone.all_objects.get(pk=phone.pk)
            # The `in_book` field for place's visibility object is expected to be enabled.
            form = VisibilityForm(instance=place.visibility)
            self.assertFalse(form.fields['visible_in_book'].disabled)
            # The `in_book` field for phone's visibility object is expected to be enabled.
            form = VisibilityForm(instance=phone.visibility)
            self.assertFalse(form.fields['visible_in_book'].disabled)

        # Case 5. available: Y, in book: Y, visible online: N.
        with self.subTest(case=5, available=True, in_book=True, visible_online=False):
            place.visibility['online_public'] = False
            place.visibility['online_authed'] = False
            place.visibility.save()
            place = Place.all_objects.get(pk=place.pk)
            phone = Phone.all_objects.get(pk=phone.pk)
            # The `in_book` field for place's visibility object is expected to be enabled.
            form = VisibilityForm(instance=place.visibility)
            self.assertFalse(form.fields['visible_in_book'].disabled)
            # The `in_book` field for phone's visibility object is expected to be enabled.
            form = VisibilityForm(instance=phone.visibility)
            self.assertFalse(form.fields['visible_in_book'].disabled)

        # Case 6. available: Y, in book: Y, deleted: Y.
        with self.subTest(case=6, available=True, in_book=True, deleted=True):
            Place.all_objects.filter(pk=place.pk).update(deleted_on=now())
            place = Place.all_objects.get(pk=place.pk)
            phone = Phone.all_objects.get(pk=phone.pk)
            self.assertTrue(place.deleted)
            # The `in_book` field for place's visibility object is expected to be disabled.
            form = VisibilityForm(instance=place.visibility)
            self.assertTrue(form.fields['visible_in_book'].disabled)
            # The `in_book` field for phone's visibility object is expected to be disabled.
            form = VisibilityForm(instance=phone.visibility)
            self.assertTrue(form.fields['visible_in_book'].disabled)

    def test_venues(self):
        form = VisibilityForm(instance=self.phone.visibility)
        test_data = [
            (
                list(form.venues()),
                [form['visible_in_book'], form['visible_online_public'], form['visible_online_authed']],
            ), (
                list(form.venues('in_book')), [form['visible_in_book']],
            ), (
                list(form.venues('online')),
                [form['visible_online_public'], form['visible_online_authed']],
            ),
        ]
        for i, (venues, expected_venues) in enumerate(test_data, start=1):
            with self.subTest(case=i):
                self.assertEqual(len(venues), len(expected_venues))
                self.assertEqual(set(venues), set(expected_venues))
                for venue in venues:
                    with self.subTest(venue=f'{type(venue)}: {venue.name}'):
                        self.assertIsInstance(venue, BoundField)
                        self.assertTrue(hasattr(venue, 'field_name'))
                        self.assertTrue(hasattr(venue, 'venue_name'))
                        self.assertEqual(venue.field_name, f'visible_{venue.venue_name}')

    def test_object(self):
        test_data = [
            (self.phone.visibility, {'title': self.phone}),
            (self.place.visibility, {'title': self.place}),
            (self.place.family_members_visibility, {'en': "family members", 'eo': "kunloĝantoj"}),
            (self.phone.profile.email_visibility, {'title': self.phone.profile.email}),
        ]
        for obj, title in test_data:
            with self.subTest(type=obj.model_type):
                form = VisibilityForm(instance=obj)
                self.assertTrue(hasattr(form, 'obj'))
                self.assertTrue(hasattr(form.obj, 'icon'))
                self.assertSurrounding(form.obj.icon, "<", ">")
                self.assertTrue(hasattr(form.obj, '__str__'))
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(str(form.obj), str(title.get('en') or title['title']))
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertEqual(str(form.obj), str(title.get('eo') or title['title']))

    def test_object_tampering(self):
        test_data = [
            self.phone.visibility,
            self.place.visibility,
            self.place.family_members_visibility,
            self.phone.profile.email_visibility,
        ]
        for obj in test_data:
            with self.subTest(type=obj.model_type):
                with self.assertRaises(ValueError) as cm:
                    form = VisibilityForm(
                        data={'visible_in_book': True, 'hint': "AbC"},
                        request_profile="profile Dummy")
                    form.obj
                self.assertEqual(
                    str(cm.exception),
                    "Form is bound but no visibility settings object was provided, "
                    "for key None and 'profile Dummy'. "
                    "This most likely indicates tampering."
                )

    def test_save(self):
        visobj = self.place.family_members_visibility
        form = VisibilityForm(data={}, instance=visobj)
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        newobj = form.save(commit=False)
        self.assertIs(newobj, visobj)

    def test_save_phone(self):
        self.phone.visibility.visible_online_public = True
        self.phone.visibility.visible_online_authed = True
        self.phone.visibility.visible_in_book = True
        self.phone.visibility.save()

        # Setting `online_authed` to False is expected to set `online_public` to
        # False as well, and leave `in_book` as is without change.
        form = VisibilityForm(
            data={
                'visible_online_public': True,
                'visible_online_authed': False,
                'visible_in_book': True,
            },
            instance=self.phone.visibility
        )
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        form.save()
        self.phone.visibility.refresh_from_db()
        self.assertFalse(self.phone.visibility.visible_online_public)
        self.assertFalse(self.phone.visibility.visible_online_authed)
        self.assertTrue(self.phone.visibility.visible_in_book)

        # Setting `online_public` to True is expected to set `online_authed` to
        # True as well, and leave `in_book` as is without change.
        form = VisibilityForm(
            data={
                'visible_online_public': True,
                'visible_online_authed': False,
                'visible_in_book': True,
            },
            instance=self.phone.visibility
        )
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        form.save()
        self.phone.visibility.refresh_from_db()
        self.assertTrue(self.phone.visibility.visible_online_public)
        self.assertTrue(self.phone.visibility.visible_online_authed)
        self.assertTrue(self.phone.visibility.visible_in_book)

        # Setting `in_book` to False is expected to change the visibility object
        # and leave `online_public`, `online_authed` as are without change.
        form = VisibilityForm(
            data={
                'visible_online_public': True,
                'visible_online_authed': True,
                'visible_in_book': False,
            },
            instance=self.phone.visibility
        )
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        form.save()
        self.phone.visibility.refresh_from_db()
        self.assertTrue(self.phone.visibility.visible_online_public)
        self.assertTrue(self.phone.visibility.visible_online_authed)
        self.assertFalse(self.phone.visibility.visible_in_book)

    def test_save_place(self):
        self.place.visibility.visible_online_public = False
        self.place.visibility.visible_online_authed = False
        self.place.visibility.visible_in_book = True
        self.place.visibility.save()

        # Setting `online_public` to True is expected to set `online_authed` to
        # True as well, and leave `in_book` as is without change.
        form = VisibilityForm(
            data={
                'visible_online_public': True,
            },
            instance=self.place.visibility
        )
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        form.save()
        self.place.visibility.refresh_from_db()
        self.assertTrue(self.place.visibility.visible_online_public)
        self.assertTrue(self.place.visibility.visible_online_authed)
        self.assertTrue(self.place.visibility.visible_in_book)

        place2stay = PlaceFactory(available=True, in_book=True)
        place2stay.visibility.refresh_from_db()
        place2stay.visibility.visible_online_public = False
        place2stay.visibility.visible_online_authed = False
        place2stay.visibility.visible_in_book = True
        place2stay.visibility.save()

        # Setting `in_book` to False is expected to update the visibility object.
        form = VisibilityForm(
            data={
                'visible_in_book': False,
            },
            instance=place2stay.visibility
        )
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        form.save()
        place2stay.visibility.refresh_from_db()
        self.assertFalse(place2stay.visibility.visible_online_public)
        self.assertFalse(place2stay.visibility.visible_online_authed)
        self.assertFalse(place2stay.visibility.visible_in_book)

        # Setting `in_book` to True is expected to change the visibility object
        # and leave `online_public`, `online_authed` as are without change.
        form = VisibilityForm(
            data={
                'visible_in_book': True,
            },
            instance=place2stay.visibility
        )
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        form.save()
        place2stay.visibility.refresh_from_db()
        self.assertFalse(place2stay.visibility.visible_online_public)
        self.assertFalse(place2stay.visibility.visible_online_authed)
        self.assertTrue(place2stay.visibility.visible_in_book)

    def test_save_email(self):
        visobj = self.place.profile.email_visibility
        visobj.visible_online_public = True
        visobj.visible_online_authed = True
        visobj.visible_in_book = True
        visobj.save()

        # Setting `online_authed` to False is expected to set `online_public` to
        # False as well, and leave `in_book` as is without change.
        form = VisibilityForm(
            data={
                'visible_online_public': True,
                'visible_online_authed': False,
            },
            instance=visobj
        )
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        form.save()
        visobj.refresh_from_db()
        self.assertFalse(visobj.visible_online_public)
        self.assertFalse(visobj.visible_online_authed)
        self.assertTrue(visobj.visible_in_book)

        # Setting `online_public` to True is expected to set `online_authed` to
        # True as well, and leave `in_book` as is without change.
        form = VisibilityForm(
            data={
                'visible_online_public': True,
                'visible_online_authed': False,
            },
            instance=visobj
        )
        self.assertTrue(form.is_valid(), msg=repr(form.errors))
        form.save()
        visobj.refresh_from_db()
        self.assertTrue(visobj.visible_online_public)
        self.assertTrue(visobj.visible_online_authed)
        self.assertTrue(visobj.visible_in_book)


@tag('forms')
class VisibilityFormSetTests(AdditionalAsserts, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.form_set = modelformset_factory(
            VisibilitySettings,
            form=VisibilityForm, formset=VisibilityFormSetBase, extra=0)

        cls.profile = ProfileFactory(with_email=True)
        cls.profile.email_visibility.refresh_from_db()

        cls.place1 = PlaceFactory(owner=cls.profile)
        cls.place1.visibility.refresh_from_db()
        cls.place1.family_members_visibility.refresh_from_db()

        cls.place2 = PlaceFactory(owner=cls.profile)
        cls.place2.visibility.refresh_from_db()
        cls.place2.family_members_visibility.refresh_from_db()
        cls.place2.family_members.add(ProfileSansAccountFactory())

        cls.place3 = PlaceFactory(owner=cls.profile)
        cls.place3.visibility.refresh_from_db()
        cls.place3.family_members_visibility.refresh_from_db()
        cls.place3.family_members.add(ProfileSansAccountFactory(first_name="", last_name=""))

        cls.place4 = PlaceFactory()  # Different owner.
        cls.place4.visibility.refresh_from_db()

        cls.place_gone = PlaceFactory(owner=cls.profile, deleted_on=now())

        cls.phone = PhoneFactory(profile=cls.profile)
        cls.phone.visibility.refresh_from_db()

        cls.phone_gone = PhoneFactory(profile=cls.profile, deleted_on=now())

    def test_invalid_init(self):
        with self.assertRaises(KeyError) as cm:
            self.form_set()
        self.assertEqual(str(cm.exception), "'profile'")

    def init_for_language_tests(self, lang, localised_hints):
        with override_settings(LANGUAGE_CODE=lang):
            formset = self.form_set(profile=self.profile)
        # The formset's queryset is expected to include visibility objects for
        # place1, place2, place2 family members, place3, phone, public email,
        # in this order.
        self.assertEqual(len(formset.queryset), 6)
        self.assertEqual(formset.queryset[0].pk, self.place1.visibility.pk)
        self.assertEqual(formset.queryset[1].pk, self.place2.visibility.pk)
        self.assertEqual(formset.queryset[2].pk, self.place2.family_members_visibility.pk)
        self.assertEqual(formset.queryset[3].pk, self.place3.visibility.pk)
        self.assertEqual(formset.queryset[4].pk, self.phone.visibility.pk)
        self.assertEqual(formset.queryset[5].pk, self.profile.email_visibility.pk)
        # The formset is expected to include 6 forms in a specific order.
        with self.subTest(case='Place 1'):
            self.assertIsInstance(formset.forms[0], VisibilityForm)
            self.assertEqual(formset.forms[0]['hint'].value(), localised_hints['place'])
            self.assertEqual(formset.forms[0]['indent'].value(), False)
        with self.subTest(case='Place 2'):
            self.assertIsInstance(formset.forms[1], VisibilityForm)
            self.assertEqual(formset.forms[1]['hint'].value(), localised_hints['place'])
            self.assertEqual(formset.forms[1]['indent'].value(), False)
        with self.subTest(case='Place 2 Family Members'):
            self.assertIsInstance(formset.forms[2], VisibilityForm)
            self.assertEqual(formset.forms[2]['hint'].value(), "")
            self.assertEqual(formset.forms[2]['indent'].value(), True)
        with self.subTest(case='Place 2'):
            self.assertIsInstance(formset.forms[3], VisibilityForm)
            self.assertEqual(formset.forms[3]['hint'].value(), localised_hints['place'])
            self.assertEqual(formset.forms[3]['indent'].value(), False)
        with self.subTest(case='Phone'):
            self.assertIsInstance(formset.forms[4], VisibilityForm)
            self.assertEqual(formset.forms[4]['hint'].value(), localised_hints['phone'])
            self.assertEqual(formset.forms[4]['indent'].value(), False)
        with self.subTest(case='Public email'):
            self.assertIsInstance(formset.forms[5], VisibilityForm)
            self.assertEqual(formset.forms[5]['hint'].value(), localised_hints['email'])
            self.assertEqual(formset.forms[5]['indent'].value(), False)
        # Verify that the formset's save method is protected in templates.
        self.assertTrue(
            hasattr(formset.save, 'alters_data')
            or hasattr(formset.save, 'do_not_call_in_templates')
        )

    def test_init_en(self):
        self.init_for_language_tests(
            'en',
            {'place': "A place in", 'phone': "Phone number", 'email': "Email address"}
        )

    def test_init_eo(self):
        self.init_for_language_tests(
            'eo',
            {'place': "Loĝejo en", 'phone': "Telefonnumero", 'email': "Retpoŝta adreso"}
        )

    def test_init_readonly(self):
        formset = self.form_set(profile=self.profile, read_only=True)
        for form in formset.forms:
            self.assertTrue(form.fields['visible_online_public'].disabled)
            self.assertTrue(form.fields['visible_online_authed'].disabled)

    def test_tampering_wrong_prefix(self):
        data = {
            'test-TOTAL_FORMS': 10,
            'test-INITIAL_FORMS': 10,
            'test-0-id': -1,
        }
        formset = self.form_set(profile=self.profile, data=data, prefix='block')
        self.assertFalse(formset.is_valid())
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                formset.non_form_errors(),
                ["Form management data is missing or has been tampered with."]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                formset.non_form_errors(),
                ["Mastrumaj datumoj de formularo mankas aŭ estis malice modifitaj."]
            )
        self.assertEqual(formset.errors, [])

    def test_tampering_too_many_forms(self):
        data = {
            'test-TOTAL_FORMS': 2,
            'test-INITIAL_FORMS': 2,
            'test-0-id': self.place4.visibility.pk,
            'test-1-id': self.place4.visibility.pk,
        }
        formset = self.form_set(profile=self.place4.profile, data=data, prefix='test')
        with self.assertRaises(IndexError) as cm:
            formset.is_valid()
        self.assertEqual(
            str(cm.exception),
            f"Form #1 does not exist in the queryset, for {self.place4.profile!r}. "
            f"This most likely indicates tampering."
        )

    def test_tampering(self):
        test_dataset = [
            {'case': "missing forms", 'id': self.phone.visibility.pk, 'expected_id': None},
            {'case': "unknown visibility id", 'id': -3},
            {'case': "visibility id of deleted object", 'id': self.phone_gone.visibility.pk},
            {'case': "visibility id of unexpected object", 'id': self.place3.family_members_visibility.pk},
            {'case': "visibility id of different user", 'id': self.place4.visibility.pk},
        ]
        for test_data in test_dataset:
            with self.subTest(case=test_data['case']):
                data = {
                    'test-TOTAL_FORMS': 2,
                    'test-INITIAL_FORMS': 2,
                    'test-0-id': test_data['id'],
                }
                formset = self.form_set(profile=self.profile, data=data, prefix='test')
                with self.assertRaises(ValueError) as cm:
                    formset.is_valid()
                self.assertEqual(
                    str(cm.exception),
                    f"Form is bound but no visibility settings object was provided, "
                    f"for key {test_data.get('expected_id', test_data['id'])} and {self.profile!r}. "
                    f"This most likely indicates tampering."
                )

    def test_valid_data(self):
        data = {
            'test-TOTAL_FORMS': 3,
            'test-INITIAL_FORMS': 3,
            'test-0-id': self.place2.family_members_visibility.pk,
            'test-1-id': self.phone.visibility.pk,
            'test-2-id': self.place1.visibility.pk,
        }
        formset = self.form_set(profile=self.profile, data=data, prefix='test')
        self.assertTrue(formset.is_valid(), msg=repr(formset.errors))
        self.assertEqual(formset.forms[0].instance.model_type, 'FamilyMembers')
        self.assertEqual(formset.forms[1].instance.model_type, 'Phone')
        self.assertEqual(formset.forms[2].instance.model_type, 'Place')
