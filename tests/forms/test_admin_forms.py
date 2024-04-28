from django.test import TestCase, tag
from django.utils.functional import Promise

from core.forms import MassMailForm


@tag('forms', 'forms-admin')
class MassMailFormTests(TestCase):
    def test_init(self):
        form = MassMailForm()
        expected_fields = [
            'subject', 'body', 'preheader', 'heading',
            'categories', 'test_email',
        ]
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(expected_fields), set(form.fields))
        # Verify the IDs of the fields and that they are marked 'required'.
        for field_name in expected_fields:
            with self.subTest(field=field_name):
                self.assertTrue(form.fields[field_name].required)
                self.assertEqual(form[field_name].auto_id, f'id_massmail-{field_name}')
        # Verify that the form does not have a save method.
        self.assertFalse(hasattr(form, 'save'))

    def test_list_of_categories(self):
        # The form's field `categories` is expected to have 7 simple choices.
        form = MassMailForm()
        for category in form.fields['categories'].choices:
            self.assertIsInstance(category, tuple)
            self.assertEqual(len(category), 2)
            self.assertIsInstance(category[0], str, msg=type(category[0]))
            self.assertIsInstance(category[1], (str, Promise), msg=type(category[1]))
        self.assertEqual(
            set(key for key, text in form.fields['categories'].choices),
            {
                'old_system', 'users_active_1y', 'users_active_2y', 'not_hosts',
                'in_book', 'not_in_book', 'test',
            }
        )
