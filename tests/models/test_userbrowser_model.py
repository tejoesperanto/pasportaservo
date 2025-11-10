from typing import cast

from django.db.models import DecimalField
from django.test import TestCase, override_settings, tag

from ..factories import UserBrowserFactory, UserFactory


@tag('models', 'auth')
class UserBrowserModelTests(TestCase):
    def test_field_max_lengths(self):
        ub = UserBrowserFactory.build()
        self.assertEqual(ub._meta.get_field('user_agent_string').max_length, 250)
        self.assertEqual(ub._meta.get_field('user_agent_hash').max_length, 32)
        self.assertEqual(ub._meta.get_field('geolocation').max_length, 50)
        self.assertEqual(ub._meta.get_field('os_name').max_length, 30)
        self.assertEqual(ub._meta.get_field('os_version').max_length, 15)
        self.assertEqual(
            cast(DecimalField, ub._meta.get_field('os_version_numeric')).decimal_places,
            35)
        self.assertEqual(ub._meta.get_field('browser_name').max_length, 30)
        self.assertEqual(ub._meta.get_field('browser_version').max_length, 15)
        self.assertEqual(
            cast(DecimalField, ub._meta.get_field('browser_version_numeric')).decimal_places,
            35)
        self.assertEqual(ub._meta.get_field('device_type').max_length, 30)

    def test_str_repr(self):
        ub = UserBrowserFactory.build(
            user=UserFactory.build(username="abcxyz", profile=None),
            browser_name="Netscape", browser_version="4.08",
            platform="windows", os_version="98")
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(str(ub), "abcxyz: Netscape 4.08 at Windows 98")
            self.assertEqual(
                str(repr(ub)),
                "<User: abcxyz · Browser: Netscape 4.08 · OS: Windows 98 · Device: PC>"
            )
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(str(ub), "abcxyz: Netscape 4.08 ĉe Windows 98")
            self.assertEqual(
                str(repr(ub)),
                "<User: abcxyz · Browser: Netscape 4.08 · OS: Windows 98 · Device: PC>"
            )

        ub = UserBrowserFactory.build(
            user=UserFactory.build(username="jekeleme", profile=None),
            browser_name="", browser_version="",
            os_name="", os_version="", device_type="")
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(str(ub), "jekeleme: ?  at ? ")
            self.assertEqual(str(repr(ub)), "<User: jekeleme · Browser:   · OS:  >")
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(str(ub), "jekeleme: ?  ĉe ? ")
            self.assertEqual(str(repr(ub)), "<User: jekeleme · Browser:   · OS:  >")

    def test_save(self):
        user = UserFactory.create(username="abcxyz", profile=None)
        test_data = (
            {'browser': "0.9.4.1", 'os': "5.1.2600.1106"},
            {'browser': "Next", 'os': "XP SP2"},
            {'browser': "", 'os': ""},
        )

        for versions in test_data:
            with self.subTest(versions=versions):
                ub = UserBrowserFactory.build(
                    user=user,
                    browser_name="Mozilla", browser_version=versions['browser'],
                    os_name="Windows", os_version=versions['os'])
                ub.save()
                self.assertIsNotNone(ub.pk)
                if versions['os']:
                    self.assertIsNotNone(ub.os_version_numeric)
                    self.assertNotEqual(ub.os_version_numeric, 0)
                else:
                    self.assertEqual(ub.os_version_numeric, 0)
                if versions['browser']:
                    self.assertIsNotNone(ub.browser_version_numeric)
                    self.assertNotEqual(ub.browser_version_numeric, 0)
                else:
                    self.assertEqual(ub.browser_version_numeric, 0)
                self.assertIsNotNone(ub.added_on)

    def test_save_partial(self):
        ub = UserBrowserFactory.create(
            user__profile=None, os_version='1.20.300', browser_version='49.6.8',
        )
        self.assertNotEqual(ub.os_version, "")
        self.assertNotEqual(ub.os_version_numeric, 0)
        self.assertNotEqual(ub.browser_version, "")
        self.assertNotEqual(ub.browser_version_numeric, 0)

        # Saving fields not related to the version of the OS or the browser is
        # expected not to save the textual and the numeric version values.
        ub.device_type = "Printer"
        ub.os_name = "IBM PrintOS"
        ub.os_version = ""
        ub.browser_version = ""
        ub.save(update_fields=('os_name', 'device_type'))
        ub.refresh_from_db()
        self.assertEqual(ub.device_type, "Printer")
        self.assertEqual(ub.os_name, "IBM PrintOS")
        self.assertEqual(ub.os_version, "1.20.300")
        self.assertNotEqual(ub.os_version_numeric, 0)
        self.assertEqual(ub.browser_version, "49.6.8")
        self.assertNotEqual(ub.browser_version_numeric, 0)

        # Saving the textual OS version field is expected to update also
        # the numeric value, and not save any other fields.
        ub.device_type = "Scanner"
        ub.os_version, previous_os_numeric = "4.50", ub.os_version_numeric
        ub.browser_version, previous_browser_numeric = "", ub.browser_version_numeric
        ub.save(update_fields=['os_version'])
        ub.refresh_from_db()
        self.assertEqual(ub.device_type, "Printer")
        self.assertEqual(ub.os_version, "4.50")
        self.assertNotEqual(ub.os_version_numeric, 0)
        self.assertNotEqual(ub.os_version_numeric, previous_os_numeric)
        self.assertEqual(ub.browser_version, "49.6.8")
        self.assertEqual(ub.browser_version_numeric, previous_browser_numeric)

        # Saving the textual browser version field is expected to update also
        # the numeric value, and not save any other fields.
        ub.device_type = "Router"
        ub.os_version, previous_os_numeric = "", ub.os_version_numeric
        ub.browser_version = "84.4.4"
        ub.save(update_fields=['browser_version'])
        ub.refresh_from_db()
        self.assertEqual(ub.device_type, "Printer")
        self.assertEqual(ub.os_version, "4.50")
        self.assertEqual(ub.os_version_numeric, previous_os_numeric)
        self.assertEqual(ub.browser_version, "84.4.4")
        self.assertNotEqual(ub.browser_version_numeric, 0)
        self.assertNotEqual(ub.browser_version_numeric, previous_browser_numeric)
