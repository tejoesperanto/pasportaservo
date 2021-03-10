from django.test import override_settings, tag

from django_webtest import WebTest

from ..factories import GenderFactory


@tag('models')
class GenderModelTests(WebTest):
    def test_field_max_lengths(self):
        gender = GenderFactory.build()
        self.assertEqual(gender._meta.get_field('name_en').max_length, 255)
        self.assertEqual(gender._meta.get_field('name').max_length, 255)

    def test_field_uniqueness(self):
        gender = GenderFactory.build()
        self.assertTrue(gender._meta.get_field('name_en').unique)
        self.assertTrue(gender._meta.get_field('name').unique)

    def test_eqality(self):
        gender = GenderFactory.build(name="forrest", name_en="gump")
        self.assertEqual(gender, GenderFactory.build(name="forrest"))
        self.assertEqual(gender, GenderFactory.build(name="forrest", name_en="curran"))
        self.assertEqual(gender, "forrest")
        self.assertNotEqual(gender, GenderFactory.build(name="bubba"))
        self.assertNotEqual(gender, GenderFactory.build(name="bubba", name_en="gump"))
        self.assertEqual("forrest", gender)
        self.assertNotEqual("bubba", gender)
        self.assertFalse(gender == 7)
        self.assertFalse(gender == id(gender))
        self.assertFalse(gender == ["forrest"])
        self.assertFalse(gender == (term for term in ["forrest"]))

    def test_str(self):
        gender_known = GenderFactory.build()
        gender_novel = GenderFactory.build(id=None, name_en="")
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(str(gender_known), gender_known.name)
            self.assertEqual(str(gender_novel), gender_novel.name)
        with override_settings(LANGUAGE_CODE='fr'):
            self.assertEqual(str(gender_known), gender_known.name_en)
            self.assertEqual(str(gender_novel), gender_novel.name)
