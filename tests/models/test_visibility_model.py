from django.db import DEFAULT_DB_ALIAS, connections
from django.db.models import CASCADE
from django.test import TestCase, override_settings, tag
from django.test.utils import CaptureQueriesContext
from django.utils import timezone, translation

from hosting.models import (
    Phone, Place, Profile, VisibilitySettings,
    VisibilitySettingsForFamilyMembers, VisibilitySettingsForPhone,
    VisibilitySettingsForPlace, VisibilitySettingsForPublicEmail,
)

from ..assertions import AdditionalAsserts
from ..factories import (
    ConditionFactory, PhoneFactory, PlaceFactory,
    ProfileFactory, ProfileSansAccountFactory,
)


@tag('models')
class VisibilityModelTests(AdditionalAsserts, TestCase):
    subclasses = {
        'Place': VisibilitySettingsForPlace,
        'FamilyMembers': VisibilitySettingsForFamilyMembers,
        'Phone': VisibilitySettingsForPhone,
        'PublicEmail': VisibilitySettingsForPublicEmail,
    }
    options = ('visible_in_book', 'visible_online_authed', 'visible_online_public')

    def test_fields(self):
        model = VisibilitySettings()
        self.assertEqual(model._meta.get_field('model_type').max_length, 25)
        with translation.override(None):
            self.assertEqual(model._meta.get_field('model_type').default, 'Unknown')
        self.assertTrue(model._meta.get_field('model_id').null)
        self.assertIs(model._meta.get_field('content_type').remote_field.on_delete, CASCADE)

    def test_str(self):
        test_data = [
            (
                "generic", VisibilitySettings(),
                {'en': "unknown", 'eo': "nekonataĵo"},
            ), (
                "place", VisibilitySettingsForPlace(model_type='Place'),
                {'en': "place", 'eo': "loĝejo"},
            ), (
                "fm", VisibilitySettingsForFamilyMembers(model_type='FamilyMembers'),
                {'en': "family members", 'eo': "kunloĝantoj"},
            ), (
                "phone", VisibilitySettingsForPhone(model_type='Phone'),
                {'en': "phone", 'eo': "telefono"},
            ), (
                "email", VisibilitySettingsForPublicEmail(model_type='PublicEmail'),
                {'en': "public email", 'eo': "publika retpoŝta adreso"},
            )
        ]
        for model_tag, model, labels in test_data:
            with self.subTest(type=model_tag):
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(str(model), f"Settings of visibility for {labels['en']}")
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertEqual(str(model), f"Agordoj de videbligo por {labels['eo']}")

    def test_repr(self):
        model = VisibilitySettings()
        self.assertEqual(repr(model), "<VisibilitySettings for Unknown@None ~ OP:N,OA:N,B:N>")

        model = VisibilitySettingsForPhone(visible_online_authed=True, visible_in_book=False)
        self.assertEqual(repr(model), "<VisibilitySettingsForPhone @None ~ OP:N,OA:T,B:F>")
        model = VisibilitySettings(model_type='Phone', visible_online_public=False)
        self.assertEqual(repr(model), "<VisibilitySettings for Phone@None ~ OP:F,OA:N,B:N>")

    def test_defaults(self):
        expected_defaults = {
            'Place': {'in_book': True, 'online_public': True, 'online_authed': True},
            'FamilyMembers': {'in_book': True, 'online_public': False, 'online_authed': True},
            'PublicEmail': {'in_book': True, 'online_public': False, 'online_authed': False},
            'Phone': {'in_book': True, 'online_public': False, 'online_authed': True},
        }
        # Verify that each visibility subtype defines visibility defaults as expected.
        for model_type in expected_defaults:
            with self.subTest(type=model_type):
                model = self.subclasses[model_type]
                for opt, expected_default in expected_defaults[model_type].items():
                    with self.subTest(opt=opt):
                        self.assertIs(model.defaults[opt], expected_default)

    def test_rules(self):
        expected_rules = {
            'Place': {'in_book': True, 'online_public': True, 'online_authed': False, 'tied_online': True},
            'FamilyMembers': {'in_book': False, 'online_public': True, 'online_authed': False},
            'PublicEmail': {'in_book': False, 'online_public': True, 'online_authed': True},
            'Phone': {'in_book': True, 'online_public': True, 'online_authed': True},
        }
        # Verify that each visibility subtype defines visibility modification rules as expected.
        for model_type in expected_rules:
            with self.subTest(type=model_type):
                model = self.subclasses[model_type]
                self.assertEqual(model.rules, expected_rules[model_type])

    def test_prep(self):
        # The `prep` method is expected to be used only from concrete subclasses.
        with self.assertRaises(TypeError) as cm:
            VisibilitySettings.prep()
        self.assertEqual(str(cm.exception), "Only specific visibility settings may be created")

        # The `prep` method is expected to create a new object in the db, and
        # return it, populated with the correct data.
        for model_type, model_class in self.subclasses.items():
            with self.subTest(type=model_type):
                with CaptureQueriesContext(connections[DEFAULT_DB_ALIAS]) as cm:
                    model = model_class.prep()
                self.assertGreaterEqual(
                    len(cm.captured_queries), 1,
                    "{} queries executed while >= 1 expected\nCaptured queries were:\n{}".format(
                        len(cm.captured_queries),
                        "\n".join(
                            f"{i}. {query['sql']}"
                            for i, query in enumerate(cm.captured_queries, start=1)
                        )
                    )
                )
                self.assertStartsWith(cm.captured_queries[-1]['sql'].upper(), 'INSERT INTO')
                self.assertIsNotNone(model.pk)
                self.assertIsNone(model.model_id)
                self.assertEqual(model.model_type, model_type)
                for opt in self.options:
                    self.assertIsNotNone(getattr(model, opt), msg=f"option {opt}")

    def test_prep_invalid_parent(self):
        containers = {
            'FamilyMembers': 'Place',
            'PublicEmail': 'Profile',
        }
        cond = ConditionFactory()
        for model_type, model_class in self.subclasses.items():
            with self.subTest(type=model_type):
                # A parent object which is not a Django Model instance is expected to
                # raise an error.
                with self.assertRaises(AssertionError) as cm:
                    model_class.prep("not a model")
                self.assertEqual(str(cm.exception), "'not a model' is not a Model instance!")
                # A parent object which is not a Django Model instance is expected to
                # raise an error.
                with self.assertRaises(AssertionError) as cm:
                    model_class.prep(VisibilitySettings)
                self.assertEqual(
                    str(cm.exception),
                    "<class 'hosting.models.VisibilitySettings'> is not a Model instance!"
                )
                # A parent object which does not correspond to the requested subtype,
                # is expected to raise an error.
                with self.assertRaises(AssertionError) as cm:
                    model_class.prep(cond)
                self.assertEndsWith(
                    str(cm.exception),
                    f"is not a hosting.models.{containers.get(model_type, model_type)}!"
                )

    def test_prep_valid_parent(self):
        profile = ProfileFactory()
        objects = {
            'Place': PlaceFactory(owner=profile),
            'FamilyMembers': PlaceFactory(owner=profile),
            'Phone': PhoneFactory(profile=profile),
            'PublicEmail': profile,
        }
        # The `prep` method is expected to create a new object in the db, and
        # return it, populated with the correct data.
        for model_type, model_class in self.subclasses.items():
            with self.subTest(type=model_type):
                model = model_class.prep(objects[model_type])
                self.assertIsNotNone(model.pk)
                self.assertEqual(model.model_id, objects[model_type].pk)
                self.assertEqual(model.model_type, model_type)
                for opt in self.options:
                    self.assertIsNotNone(getattr(model, opt), msg=f"option {opt}")

    def test_specific_models_method(self):
        self.assertEqual(VisibilitySettings.specific_models(), self.subclasses)
        self.assertEqual(VisibilitySettingsForFamilyMembers.specific_models(), self.subclasses)

    def test_type_method(self):
        with self.assertRaises(TypeError) as cm:
            VisibilitySettings.type()
        self.assertEqual(
            str(cm.exception),
            "Model type is only defined for specific visibility settings"
        )

        for model_type, model in self.subclasses.items():
            self.assertEqual(model.type(), model_type, msg=f"model {model}")

    def test_as_specific_method(self):
        for model_type, model_class in self.subclasses.items():
            with self.subTest(type=model_type):
                model = model_class()
                result = model.as_specific()
                self.assertIs(result, model)
                self.assertIs(result.__class__, model_class)

                model = VisibilitySettings(model_type=model_type)
                result = model.as_specific()
                self.assertIs(result.__class__, model_class)

        model = VisibilitySettings(model_type='Dummy')
        self.assertRaises(NameError, model.as_specific)

    def test_venues_method(self):
        expected = set(opt[len('visible_'):] for opt in self.options)
        self.assertEqual(set(VisibilitySettings.venues()), expected)
        for model in self.subclasses.values():
            self.assertEqual(set(model.venues()), expected, msg=f"\nmodel {model}")

    def test_getitem(self):
        model = VisibilitySettings()
        for opt in self.options:
            self.assertEqual(model[opt[len('visible_'):]], getattr(model, opt))
        # Trying to get an unknown visibility option is expected to raise an error.
        with self.assertRaises(KeyError) as cm:
            model['dummy']
        self.assertEqual(cm.exception.args[0], "Unknown venue 'dummy'")
        with self.assertRaises(KeyError) as cm:
            model['model_type']
        self.assertEqual(cm.exception.args[0], "Unknown venue 'model_type'")

    def test_setitem(self):
        model = VisibilitySettings()
        for opt in self.options:
            self.assertIsNone(getattr(model, opt), msg=f"option {opt}")
            model[opt[len('visible_'):]] = False
            self.assertFalse(getattr(model, opt), msg=f"option {opt}")
        # Trying to set an unknown visibility option is expected to raise an error.
        with self.assertRaises(KeyError) as cm:
            model['content_type'] = True
        self.assertEqual(cm.exception.args[0], "Unknown venue 'content_type'")

    def test_concealed(self):
        model = VisibilitySettings()
        # When none of the visibility options is set, the object is expected
        # to be considered concealed.
        for opt in self.options:
            self.assertIsNone(getattr(model, opt), msg=f"option {opt}")
        self.assertTrue(model.concealed)
        # When all visibility options are set to False, the object is expected
        # to be considered concealed.
        for opt in self.options:
            setattr(model, opt, False)
        self.assertTrue(model.concealed)
        # When one or more visibility options are set to True, the object is
        # expected to be considered revealed (not concealed).
        for opt in self.options:
            with self.subTest(setting=f"{opt} <- T"):
                setattr(model, opt, True)
                self.assertFalse(model.concealed)

    def test_printable_default(self):
        # The default printable (in book) setting is expected to be True.
        self.assertTrue(VisibilitySettings().printable)

    def test_printable_place(self):
        # A place not configured to appear in book and its tenants
        # are expected to be not printable.
        place = PlaceFactory(in_book=False)
        place = Place.all_objects.get(pk=place.pk)
        self.assertFalse(place.visibility.printable)
        self.assertFalse(place.family_members_visibility.printable)

        # An unavailable place configured to appear in book and its tenants
        # are expected to be not printable.
        Place.all_objects.filter(pk=place.pk).update(in_book=True, available=False)
        place = Place.all_objects.get(pk=place.pk)
        self.assertFalse(place.visibility.printable)
        self.assertFalse(place.family_members_visibility.printable)

        # An available place configured to appear in book and its tenants
        # are expected to be printable.
        Place.all_objects.filter(pk=place.pk).update(in_book=True, available=True)
        place = Place.all_objects.get(pk=place.pk)
        self.assertTrue(place.visibility.printable)
        self.assertTrue(place.family_members_visibility.printable)

        # Hiding the place online is not expected to affect printability.
        place.visibility.visible_online_public = False
        place.visibility.save()
        place = Place.all_objects.get(pk=place.pk)
        self.assertTrue(place.visibility.printable)
        self.assertTrue(place.family_members_visibility.printable)

        # An available place configured to appear in book, which was deleted,
        # and its tenants are expected to be not printable.
        Place.all_objects.filter(pk=place.pk).update(deleted_on=timezone.now())
        place = Place.all_objects.get(pk=place.pk)
        self.assertFalse(place.visibility.printable)
        self.assertFalse(place.family_members_visibility.printable)

    def test_printable_profile(self):
        # A profile email or phone for profile with no places and no user
        # is expected to be not printable.
        profile = ProfileSansAccountFactory()
        profile = Profile.all_objects.get(pk=profile.pk)
        phone = PhoneFactory(profile=profile)
        phone = Phone.all_objects.get(pk=phone.pk)
        self.assertFalse(profile.email_visibility.printable)
        self.assertFalse(phone.visibility.printable)

        # A profile email or phone for profile with no places
        # is expected to be not printable.
        profile = ProfileFactory()
        profile = Profile.all_objects.get(pk=profile.pk)
        Phone.all_objects.filter(pk=phone.pk).update(profile=profile)
        phone = Phone.all_objects.get(pk=phone.pk)
        self.assertFalse(profile.email_visibility.printable)
        self.assertFalse(phone.visibility.printable)

        # A profile email or phone for profile with an unavailable place not
        # configured to appear in book is expected to be not printable.
        place = PlaceFactory(in_book=False, available=False)
        place = Place.all_objects.get(pk=place.pk)
        Phone.all_objects.filter(pk=phone.pk).update(profile=place.profile)
        phone = Phone.all_objects.get(pk=phone.pk)
        self.assertFalse(place.profile.email_visibility.printable)
        self.assertFalse(phone.visibility.printable)

        # A profile email or phone for profile with an unavailable place
        # configured to appear in book is expected to be not printable.
        Place.all_objects.filter(pk=place.pk).update(in_book=True, available=False)
        place = Place.all_objects.get(pk=place.pk)
        phone = Phone.all_objects.get(pk=phone.pk)
        self.assertFalse(place.profile.email_visibility.printable)
        self.assertFalse(phone.visibility.printable)

        # A profile email or phone for profile with an available place not
        # configured to appear in book is expected to be printable.
        Place.all_objects.filter(pk=place.pk).update(in_book=False, available=True)
        place = Place.all_objects.get(pk=place.pk)
        phone = Phone.all_objects.get(pk=phone.pk)
        self.assertTrue(place.profile.email_visibility.printable)
        self.assertTrue(phone.visibility.printable)

        # Hiding the place online is not expected to affect printability.
        place.visibility.visible_online_public = False
        place.visibility.save()
        place = Place.all_objects.get(pk=place.pk)
        phone = Phone.all_objects.get(pk=phone.pk)
        self.assertTrue(place.profile.email_visibility.printable)
        self.assertTrue(phone.visibility.printable)

        # A profile email or phone for profile with an available place that
        # was deleted is expected to be not printable.
        Place.all_objects.filter(pk=place.pk).update(deleted_on=timezone.now())
        place = Place.all_objects.get(pk=place.pk)
        phone = Phone.all_objects.get(pk=phone.pk)
        self.assertFalse(place.profile.email_visibility.printable)
        self.assertFalse(phone.visibility.printable)
