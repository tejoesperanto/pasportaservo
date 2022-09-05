from django.conf import settings
from django.test import override_settings, tag
from django.utils.functional import lazy

from django_webtest import WebTest

from ..assertions import AdditionalAsserts
from ..factories import PhoneFactory
from .test_managers import TrackingManagersTests


@tag('models', 'phone')
class PhoneModelTests(AdditionalAsserts, TrackingManagersTests, WebTest):
    factory = PhoneFactory

    @classmethod
    def setUpTestData(cls):
        cls.phone = PhoneFactory()

    def test_field_max_lengths(self):
        self.assertEqual(self.phone._meta.get_field('comments').max_length, 255)
        self.assertEqual(self.phone._meta.get_field('type').max_length, 3)

    def test_owner(self):
        self.assertIs(self.phone.owner, self.phone.profile)

    def test_icon(self):
        # SIDE EFFECT: self.phone.type is altered but not saved to database.
        mock_translation = lazy(
            lambda text: "neindikita tipo" if settings.LANGUAGE_CODE == 'eo' else text,
            str
        )
        test_data = self.phone.PhoneType.choices
        test_data += [('x', "x"), ('', mock_translation("type not indicated"))]
        for phone_type, phone_type_title in test_data:
            with self.subTest(phone_type=phone_type):
                self.phone.type = phone_type
                for lang in ['en', 'eo']:
                    with override_settings(LANGUAGE_CODE=lang):
                        self.assertSurrounding(self.phone.icon, "<span ", "></span>")
                        title = phone_type_title.capitalize() if phone_type else phone_type_title
                        self.assertIn(f" title=\"{title}\" ", self.phone.icon)

    def test_str(self):
        self.assertEqual(str(self.phone), self.phone.number.as_international)

    def test_repr(self):
        self.assertSurrounding(repr(self.phone), "<Phone:", f"|p#{self.phone.profile.pk}>")

    def test_rawdisplay(self):
        # SIDE EFFECT: self.phone.type is altered but not saved to database.
        test_data = self.phone.PhoneType.values + ['x', '', None]
        for phone_type in test_data:
            with self.subTest(phone_type=phone_type):
                self.phone.type = phone_type
                expected_type = phone_type or "(?)"
                self.assertEqual(
                    self.phone.rawdisplay(),
                    f"{expected_type}: {self.phone.number.as_international}"
                )
