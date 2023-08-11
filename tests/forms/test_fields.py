from django import forms
from django.db import models
from django.test import TestCase, modify_settings, tag

from hosting.fields import MultiNullBooleanFormField
from hosting.models import Condition
from hosting.widgets import MultiNullBooleanSelects

from ..assertions import AdditionalAsserts
from ..factories import ConditionFactory


@tag('forms', 'form-fields')
class MultiNullBooleanFieldTests(AdditionalAsserts, TestCase):
    ROUND_BAKED_GOODS_OFFER = [(10, "Veggie"), (20, "Funghi"), (30, "Margarita"), (40, "Caprese")]
    NULL_BOOLEAN_CHOICES = [('true', "yes please"), ('false', "no way"), ('unknown', "whatever")]

    def test_init(self):
        field = MultiNullBooleanFormField(
            forms.ChoiceField(choices=self.ROUND_BAKED_GOODS_OFFER),
            self.NULL_BOOLEAN_CHOICES)
        # The number of subfields is expected to be equal to the number of choices.
        self.assertLength(field.fields, 4)
        # Each subfield is expected to be a NullBooleanField.
        for f in field.fields:
            self.assertIsInstance(f, forms.NullBooleanField)
            self.assertFalse(f.required)
        self.assertTrue(field.required)
        # None is expected to not be included in `empty_values`, because it is
        # a valid value.
        self.assertNotIn(None, field.empty_values)

    def test_validation(self):
        field = MultiNullBooleanFormField(
            forms.ChoiceField(choices=self.ROUND_BAKED_GOODS_OFFER),
            self.NULL_BOOLEAN_CHOICES)

        # Empty values are expected to fail the validation, because by default
        # the field has required=True.
        with self.assertRaises(forms.ValidationError) as cm:
            field.clean([])
        self.assertEqual(getattr(cm.exception, 'code', None), 'required')
        with self.assertRaises(forms.ValidationError) as cm:
            field.clean('')
        self.assertEqual(getattr(cm.exception, 'code', None), 'required')

        # Non-empty values are expected to pass the validation, with anything
        # not recognised as True or False treated as unknown, thus None.
        with self.assertNotRaises(forms.ValidationError):
            cleaned_value = field.clean(['x', 'true'])
        self.assertEqual(
            list(cleaned_value),
            [(10, None), (20, True), (30, None), (40, None)]
        )
        # A non-empty value which is not a list is expected to be invalid.
        with self.assertRaises(forms.ValidationError) as cm:
            field.clean(' z,y,false ')
        self.assertEqual(getattr(cm.exception, 'code', None), 'invalid')

        field = MultiNullBooleanFormField(
            forms.ChoiceField(choices=self.ROUND_BAKED_GOODS_OFFER, required=False),
            self.NULL_BOOLEAN_CHOICES)

        # Empty values for a not required field are expected to be valid.
        with self.assertNotRaises(forms.ValidationError):
            cleaned_value = field.clean([])
        self.assertEqual(
            list(cleaned_value),
            [(10, None), (20, None), (30, None), (40, None)]
        )
        with self.assertNotRaises(forms.ValidationError):
            cleaned_value = field.clean('')
        self.assertEqual(
            list(cleaned_value),
            [(10, None), (20, None), (30, None), (40, None)]
        )

    def test_validation_on_disabled_field(self):
        field = MultiNullBooleanFormField(
            forms.ChoiceField(choices=self.ROUND_BAKED_GOODS_OFFER, required=False),
            self.NULL_BOOLEAN_CHOICES, disabled=True)

        with self.assertNotRaises(forms.ValidationError):
            cleaned_value = field.clean([None, 0, False])
        self.assertEqual(
            list(cleaned_value),
            [(10, None), (20, False), (30, False), (40, None)]
        )
        with self.assertNotRaises(forms.ValidationError):
            cleaned_value = field.clean(' z,y,false ')
        self.assertEqual(
            list(cleaned_value),
            [(10, None), (20, None), (30, False), (40, None)]
        )

        with self.assertNotRaises(forms.ValidationError):
            cleaned_value = field.clean([])
        self.assertEqual(
            list(cleaned_value),
            [(10, None), (20, None), (30, None), (40, None)]
        )
        with self.assertNotRaises(forms.ValidationError):
            cleaned_value = field.clean('')
        self.assertEqual(
            list(cleaned_value),
            [(10, None), (20, None), (30, None), (40, None)]
        )

    def widget_tests(self, form):
        with self.subTest(form=form.__class__.__name__):
            # The default form field widget is expected to be MultiNullBooleanSelects.
            self.assertIsInstance(form.fields['extra_order'].widget, MultiNullBooleanSelects)
            # The choices are expected to be split into separate widgets.
            self.assertLength(form.fields['extra_order'].widget.widgets, 4)
            # Widget name suffixes are expected to be the choice values.
            self.assertEqual(
                form.fields['extra_order'].widget.widgets_names,
                [f'_{value}' for value, label in form.fields['pizza_choices'].choices]
            )
            # Each choice widget is expected to have the 3 null boolean options,
            # in the order specified in the field's definition.
            original_choices = list(form.fields['pizza_choices'].choices)
            for i, w in enumerate(form.fields['extra_order'].widget.widgets):
                self.assertEqual(w.label, original_choices[i][1])
                self.assertEqual([k for k, label in w.choices], ['true', 'false', 'unknown'])

            # The HTML element IDs of the choice widgets are expected to be numbered
            # from 0 to number of choices, while their names are expected to have the
            # choice value appended.
            rendered_form = form.as_p()
            for i in range(4):
                self.assertIn(f'id="id_extra_order_{i}"', rendered_form)
                self.assertIn(f'name="extra_order_{original_choices[i][0]}"', rendered_form)

    def test_widget_for_simple_form(self):
        class TastyForm(forms.Form):
            pizza_choices = forms.ChoiceField(choices=self.ROUND_BAKED_GOODS_OFFER)
            extra_order = MultiNullBooleanFormField(pizza_choices, self.NULL_BOOLEAN_CHOICES)

        self.widget_tests(TastyForm())

    @modify_settings(INSTALLED_APPS={
        'append': 'tests.forms.test_fields',
    })
    def test_widget_for_model_form(self):
        class TastyModel(models.Model):
            pizza_choices = models.CharField(
                choices=self.ROUND_BAKED_GOODS_OFFER, blank=False, default=30)

        class TastyModelForm(forms.ModelForm):
            class Meta:
                model = TastyModel
                fields = '__all__'

            def __init__(form_self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                form_self.fields['extra_order'] = MultiNullBooleanFormField(
                    form_self.fields['pizza_choices'], self.NULL_BOOLEAN_CHOICES
                )

        self.widget_tests(TastyModelForm())

    @modify_settings(INSTALLED_APPS={
        'append': 'tests.forms.test_fields',
    })
    def test_widget_for_foreign_key(self):
        Condition.objects.all().delete()
        ConditionFactory.create_batch(4)

        class MightBeTastyModel(models.Model):
            pizza_choices = models.ManyToManyField(Condition, blank=False)

        class TastyByReferenceModelForm(forms.ModelForm):
            class Meta:
                model = MightBeTastyModel
                fields = ['pizza_choices']

            def __init__(form_self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                form_self.fields['extra_order'] = MultiNullBooleanFormField(
                    form_self.fields['pizza_choices'], self.NULL_BOOLEAN_CHOICES
                )

        self.widget_tests(TastyByReferenceModelForm())
