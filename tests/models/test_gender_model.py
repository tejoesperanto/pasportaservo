from django.test import override_settings, tag

from django_webtest import WebTest

from ..factories import GenderFactory


@tag('models')
class GenderModelTests(WebTest):
    def test_field_max_lengths(self):
        gender = GenderFactory.build()
        self.assertEquals(gender._meta.get_field('name_en').max_length, 255)
        self.assertEquals(gender._meta.get_field('name').max_length, 255)

    def test_field_uniqueness(self):
        gender = GenderFactory.build()
        self.assertTrue(gender._meta.get_field('name_en').unique)
        self.assertTrue(gender._meta.get_field('name').unique)

    def test_eqality(self):
        gender = GenderFactory.build(name="forrest", name_en="gump")
        self.assertEquals(gender, GenderFactory.build(name="forrest"))
        self.assertEquals(gender, GenderFactory.build(name="forrest", name_en="curran"))
        self.assertEquals(gender, "forrest")
        self.assertNotEquals(gender, GenderFactory.build(name="bubba"))
        self.assertNotEquals(gender, GenderFactory.build(name="bubba", name_en="gump"))
        self.assertEquals("forrest", gender)
        self.assertNotEquals("bubba", gender)
        self.assertFalse(gender == 7)
        self.assertFalse(gender == id(gender))
        self.assertFalse(gender == ["forrest"])
        self.assertFalse(gender == (term for term in ["forrest"]))

    def test_str(self):
        gender_known = GenderFactory.build()
        gender_novel = GenderFactory.build(id=None, name_en="")
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEquals(str(gender_known), gender_known.name)
            self.assertEquals(str(gender_novel), gender_novel.name)
        with override_settings(LANGUAGE_CODE='fr'):
            self.assertEquals(str(gender_known), gender_known.name_en)
            self.assertEquals(str(gender_novel), gender_novel.name)
