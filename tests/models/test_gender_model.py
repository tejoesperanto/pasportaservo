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

    def test_str(self):
        gender = GenderFactory.build()
        self.assertEquals(str(gender), gender.name)
