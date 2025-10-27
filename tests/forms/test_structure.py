from django import forms
from django.test import TestCase

from crispy_forms.helper import FormHelper

from core.mixins import HtmlIdFormMixin

from ..assertions import AdditionalAsserts


class HtmlIdFormMixinTests(AdditionalAsserts, TestCase):
    class SimpleForm(HtmlIdFormMixin, forms.Form):
        name = forms.CharField(required=False)

    class CrispyForm(HtmlIdFormMixin, forms.Form):
        name = forms.CharField(required=False)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.helper = FormHelper(self)

    def test_regular_form(self):
        form = self.SimpleForm()
        self.assertTrue(hasattr(form, 'html_id'))
        self.assertEqual(form.html_id, 'id_simple_form')

        # Manually setting the ID is expected to preserve the chosen value.
        form.html_id = 'custom-id-xyz'
        self.assertEqual(form.html_id, 'custom-id-xyz')

        # Deleting the property is expected to revert to the generated value.
        del form.html_id
        with self.assertNotRaises(AttributeError):
            del form.html_id  # Deleting twice is expected to work.
        self.assertTrue(hasattr(form, 'html_id'))
        self.assertEqual(form.html_id, 'id_simple_form')
        # Ensure that the value is not stale.
        self.assertEqual(form.html_id, 'id_simple_form')

    def test_crispy_form(self):
        # A form without an ID set via FormHelper is expected to have the
        # default (generated) ID value.
        form_gen_id = self.CrispyForm()
        self.assertTrue(hasattr(form_gen_id, 'html_id'))
        self.assertEqual(form_gen_id.html_id, 'id_crispy_form')
        # A form with an ID set via FormHelper is expected to have the chosen
        # ID value.
        form_set_id = self.CrispyForm()
        form_set_id.helper.form_id = 'id_crunchy'
        self.assertTrue(hasattr(form_set_id, 'html_id'))
        self.assertEqual(form_set_id.html_id, 'id_crunchy')
        # Modifying the ID in FormHelper is not expected to alter the already
        # existing ID value.
        form_set_id.helper.form_id = 'id_crumbly'
        self.assertEqual(form_set_id.html_id, 'id_crunchy')

        # Manually setting the ID is expected to preserve the chosen value.
        form_gen_id.html_id = 'custom-id-xyz'
        self.assertEqual(form_gen_id.html_id, 'custom-id-xyz')
        form_set_id.html_id = 'custom-id-cba'
        self.assertEqual(form_set_id.html_id, 'custom-id-cba')

        # Deleting the property on a form without FormHelper's ID is expected
        # to revert to the generated value.
        del form_gen_id.html_id
        with self.assertNotRaises(AttributeError):
            del form_gen_id.html_id  # Deleting twice is expected to work.
        self.assertTrue(hasattr(form_gen_id, 'html_id'))
        self.assertEqual(form_gen_id.html_id, 'id_crispy_form')
        # Ensure that the value is not stale.
        self.assertEqual(form_gen_id.html_id, 'id_crispy_form')

        # Deleting the property on a form with a FormHelper ID is expected
        # to revert to that ID value.
        del form_set_id.html_id
        with self.assertNotRaises(AttributeError):
            del form_set_id.html_id  # Deleting twice is expected to work.
        self.assertTrue(hasattr(form_set_id, 'html_id'))
        self.assertEqual(form_set_id.html_id, 'id_crumbly')
        # Ensure that the value is not stale.
        self.assertEqual(form_set_id.html_id, 'id_crumbly')

    def test_multiple_instances(self):
        self.assertEqual(
            getattr(self.SimpleForm(), 'html_id'),
            getattr(self.SimpleForm(), 'html_id')
        )
        self.assertEqual(
            getattr(self.CrispyForm(), 'html_id'),
            getattr(self.CrispyForm(), 'html_id')
        )
        form_gen_id = self.CrispyForm()
        form_set_id = self.CrispyForm()
        form_set_id.helper.form_id = 'cracklingform'
        self.assertNotEqual(form_gen_id.html_id, form_set_id.html_id)

    def test_helper_assignment(self):
        form = self.SimpleForm()
        form.helper = FormHelper(form)  # type: ignore[attr-defined]
        self.assertEqual(form.html_id, 'id_simple_form')

        # Modifying the ID in FormHelper is not expected to alter the already
        # existing ID value.
        form.helper.form_id = 'simpleton-form'  # type: ignore[attr-defined]
        self.assertEqual(form.html_id, 'id_simple_form')
        # Deleting the property is expected to revert to the fixed FormHelper
        # ID value.
        del form.html_id
        self.assertEqual(form.html_id, 'simpleton-form')
        # Deleting the property is expected to revert to the generated value,
        # when a FormHelper ID value is not set.
        form.helper.form_id = ''  # type: ignore[attr-defined]
        del form.html_id
        self.assertEqual(form.html_id, 'id_simple_form')
