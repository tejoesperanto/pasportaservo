from django_webtest import WebTest

from ..factories import GenderFactory


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
        gender = GenderFactory.build()
        self.assertEquals(str(gender), gender.name)
