from django.test import TestCase, override_settings, tag

from ..factories import ConditionFactory


@tag('models')
class ConditionModelTests(TestCase):
    def test_field_max_lengths(self):
        cond = ConditionFactory()
        self.assertEqual(cond._meta.get_field('category').max_length, 15)
        self.assertEqual(cond._meta.get_field('name_en').max_length, 255)
        self.assertEqual(cond._meta.get_field('name').max_length, 255)
        self.assertEqual(cond._meta.get_field('abbr').max_length, 20)

    def test_str(self):
        cond = ConditionFactory()
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(str(cond), cond.name_en)
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(str(cond), cond.name)

    def test_absolute_url(self):
        cond = ConditionFactory()
        expected_urls = {
            'eo': '/admin/kond/{}/',
            'en': '/admin/condition/{}/',
        }
        for lang in expected_urls:
            with override_settings(LANGUAGE_CODE=lang):
                with self.subTest(LANGUAGE_CODE=lang):
                    self.assertEqual(
                        cond.get_absolute_url(),
                        expected_urls[lang].format(cond.pk)
                    )
