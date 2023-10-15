from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.test import TestCase, modify_settings, override_settings, tag

from hosting.fields import RangeIntegerField, StyledEmailField

from ..assertions import AdditionalAsserts


@tag('models', 'fields')
class StyledEmailFieldTests(AdditionalAsserts, TestCase):
    @classmethod
    @modify_settings(INSTALLED_APPS={
        'append': 'tests.models.test_fields',
    })
    def setUpClass(cls):
        super().setUpClass()

        class Guest(Model):
            email = StyledEmailField("contact email", blank=True)

        cls.GuestModel = Guest

    def test_icon(self):
        field = self.GuestModel._meta.get_field('email')
        self.assertSurrounding(field.icon, "<span ", "></span>")
        with override_settings(LANGUAGE_CODE='en'):
            self.assertIn(' title="Email address"', field.icon)
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertIn(' title="Retpoŝta adreso"', field.icon)


@tag('models', 'fields')
class RangeIntegerFieldTests(AdditionalAsserts, TestCase):
    @classmethod
    @modify_settings(INSTALLED_APPS={
        'append': 'tests.models.test_fields',
    })
    def setUpClass(cls):
        super().setUpClass()

        class Dummy(Model):
            count_dummies = RangeIntegerField("number of dummies", min_value=1, max_value=9, null=True, blank=True)
            count_shrooms = RangeIntegerField("number of mushrooms", min_value="zero", max_value=100.23)
            count_impossible = RangeIntegerField("m.c. escher", min_value=100, max_value=50, null=True, blank=True)

        cls.DummyModel = Dummy

    def test_init(self):
        test_data = {
            'count_dummies': {'verbose_name': "number of dummies", 'min_value': 1, 'max_value': 9},
            'count_shrooms': {'verbose_name': "number of mushrooms", 'min_value': None, 'max_value': None},
        }
        # The fields are expected to have the `min_value` and `max_value` attributes set.
        # The values of the attributes are expected to be None when non-integers are provided at init.
        for field_name, field_settings in test_data.items():
            field = self.DummyModel._meta.get_field(field_name)
            for param in field_settings:
                with self.subTest(field=field_name, param=param):
                    self.assertTrue(hasattr(field, param))
                    self.assertEqual(getattr(field, param), field_settings[param])

    def test_deconstruct(self):
        # When deconstructing a model field, properly set minimum and maximum values
        # are expected to be included in kwargs.
        _, _, _, kwargs = self.DummyModel._meta.get_field('count_dummies').deconstruct()
        self.assertIn('min_value', kwargs)
        self.assertEqual(kwargs['min_value'], 1)
        self.assertIn('max_value', kwargs)
        self.assertEqual(kwargs['max_value'], 9)

        # When deconstructing a model field, improperly set minimum and maximum values
        # are expected to be omitted from kwargs.
        _, _, _, kwargs = self.DummyModel._meta.get_field('count_shrooms').deconstruct()
        self.assertNotIn('min_value', kwargs)
        self.assertNotIn('max_value', kwargs)

    def test_internal_type(self):
        # The internal type of the model field is expected to be IntegerField.
        self.assertEqual(
            self.DummyModel._meta.get_field('count_dummies').get_internal_type(),
            'IntegerField'
        )

    def test_min_value(self):
        model = self.DummyModel()

        # A model field with minimum value properly set is expected to reject a lower value.
        model.count_dummies = 0
        with self.assertRaises(ValidationError) as cm:
            model.clean_fields()
        self.assertIn('count_dummies', cm.exception.message_dict)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                cm.exception.message_dict['count_dummies'],
                ["Ensure this value is greater than or equal to 1."]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                cm.exception.message_dict['count_dummies'],
                ["Certigu ke ĉi tiu valoro estas pli ol aŭ egala al 1."]
            )

        # A model field with minimum value properly set is expected to accept a higher value.
        model.count_dummies = 5
        with self.assertNotRaises(ValidationError):
            model.clean_fields(exclude=['count_shrooms'])

        # A model field with minimum value improperly set is expected to accept any integer.
        model.count_shrooms = -17
        with self.assertNotRaises(ValidationError):
            model.clean_fields(exclude=['count_dummies'])

    def test_max_value(self):
        model = self.DummyModel()

        # A model field with maximum value properly set is expected to reject a higher value.
        model.count_dummies = 10
        with self.assertRaises(ValidationError) as cm:
            model.clean_fields()
        self.assertIn('count_dummies', cm.exception.message_dict)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                cm.exception.message_dict['count_dummies'],
                ["Ensure this value is less than or equal to 9."]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                cm.exception.message_dict['count_dummies'],
                ["Certigu ke ĉi tiu valoro estas malpli ol aŭ egala al 9."]
            )

        # A model field with maximum value properly set is expected to accept a lower value.
        model.count_dummies = 5
        with self.assertNotRaises(ValidationError):
            model.clean_fields(exclude=['count_shrooms'])

        # A model field with maximum value improperly set is expected to accept any integer.
        model.count_shrooms = 1586
        with self.assertNotRaises(ValidationError):
            model.clean_fields(exclude=['count_dummies'])

    def test_min_max_correlation(self):
        # A model field with minimum-maximum values set incongruently (i.e., min > max)
        # is expected to reject any value.
        model = self.DummyModel()

        model.count_impossible = 75
        with self.assertRaises(ValidationError) as cm:
            model.clean_fields(exclude=['count_dummies', 'count_shrooms'])
        self.assertIn('count_impossible', cm.exception.message_dict)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                cm.exception.message_dict['count_impossible'],
                [
                    'Ensure this value is greater than or equal to 100.',
                    'Ensure this value is less than or equal to 50.',
                ]
            )

        model.count_impossible = 50
        with self.assertRaises(ValidationError) as cm:
            model.clean_fields(exclude=['count_dummies', 'count_shrooms'])
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                cm.exception.message_dict,
                {'count_impossible': ["Ensure this value is greater than or equal to 100."]}
            )

        model.count_impossible = 100
        with self.assertRaises(ValidationError) as cm:
            model.clean_fields(exclude=['count_dummies', 'count_shrooms'])
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                cm.exception.message_dict,
                {'count_impossible': ["Ensure this value is less than or equal to 50."]}
            )

    def test_form_field(self):
        # The corresponding form field is expected to be IntegerField.
        field = self.DummyModel._meta.get_field('count_dummies').formfield()
        self.assertIsInstance(field, forms.fields.IntegerField)

        class DummyForm(forms.ModelForm):
            class Meta:
                model = self.DummyModel
                fields = '__all__'

        form = DummyForm()
        self.assertTrue(hasattr(form.fields['count_dummies'], 'min_value'))
        self.assertTrue(hasattr(form.fields['count_dummies'], 'max_value'))
        # The corresponding form widget is expected to be NumberInput,
        # with `min` and `max` attributes set.
        self.assertIsInstance(form.fields['count_dummies'].widget, forms.widgets.NumberInput)
        self.assertIn('min', form.fields['count_dummies'].widget.attrs)
        self.assertIn('max', form.fields['count_dummies'].widget.attrs)

        # Form validation for values outside the bounds defined in the model is expected to fail.
        form = DummyForm({'count_dummies': -20, 'count_shrooms': 5000})
        self.assertFalse(form.is_valid())
        self.assertIn('count_dummies', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors['count_dummies'],
                ["Ensure this value is greater than or equal to 1."]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors['count_dummies'],
                ["Certigu ke ĉi tiu valoro estas pli ol aŭ egala al 1."]
            )
        form = DummyForm({'count_dummies': +20, 'count_shrooms': -9999})
        self.assertFalse(form.is_valid())
        self.assertIn('count_dummies', form.errors)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(
                form.errors['count_dummies'],
                ["Ensure this value is less than or equal to 9."]
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(
                form.errors['count_dummies'],
                ["Certigu ke ĉi tiu valoro estas malpli ol aŭ egala al 9."]
            )
