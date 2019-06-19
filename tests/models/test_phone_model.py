from django_webtest import WebTest

from ..factories import PhoneFactory


class PhoneModelTests(WebTest):
    def test_field_max_lengths(self):
        phone = PhoneFactory()
        self.assertEquals(phone._meta.get_field('comments').max_length, 255)
        self.assertEquals(phone._meta.get_field('type').max_length, 3)

    def test_owner(self):
        phone = PhoneFactory()
        self.assertIs(phone.owner, phone.profile)

    def test_str(self):
        phone = PhoneFactory()
        self.assertEquals(str(phone), phone.number.as_international)
