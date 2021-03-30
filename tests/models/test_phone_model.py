from django.test import override_settings, tag

from django_webtest import WebTest

from hosting.models import PHONE_TYPE_CHOICES

from ..assertions import AdditionalAsserts
from ..factories import PhoneFactory
from .test_managers import TrackingManagersTests


@tag('models', 'phone')
class PhoneModelTests(AdditionalAsserts, TrackingManagersTests, WebTest):
    factory = PhoneFactory

    def test_field_max_lengths(self):
        phone = PhoneFactory()
        self.assertEqual(phone._meta.get_field('comments').max_length, 255)
        self.assertEqual(phone._meta.get_field('type').max_length, 3)

    def test_owner(self):
        phone = PhoneFactory()
        self.assertIs(phone.owner, phone.profile)

    @override_settings(LANGUAGE_CODE='en')
    def test_icon(self):
        phone = PhoneFactory.build()
        test_data = PHONE_TYPE_CHOICES + (('x', "x"), ('', "type not indicated"))
        for phone_type, phone_type_title in test_data:
            with self.subTest(phone_type=phone_type):
                phone.type = phone_type
                self.assertSurrounding(phone.icon, "<span ", "></span>")
                title = phone_type_title.capitalize() if phone_type else phone_type_title
                self.assertIn(f" title=\"{title}\" ", phone.icon)

    def test_str(self):
        phone = PhoneFactory()
        self.assertEqual(str(phone), phone.number.as_international)

    def test_repr(self):
        phone = PhoneFactory()
        self.assertSurrounding(repr(phone), "<Phone:", f"|p#{phone.profile.pk}>")

    def test_rawdisplay(self):
        phone = PhoneFactory.build()
        test_data = [t[0] for t in PHONE_TYPE_CHOICES] + ['x', '', None]
        for phone_type in test_data:
            with self.subTest(phone_type=phone_type):
                phone.type = phone_type
                expected_type = phone_type or "(?)"
                self.assertEqual(
                    phone.rawdisplay(),
                    f"{expected_type}: {phone.number.as_international}"
                )
