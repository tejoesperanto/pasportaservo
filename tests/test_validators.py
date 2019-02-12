from django.core.exceptions import ValidationError
from django.test import TestCase

from hosting.validators import (
    validate_not_all_caps, validate_not_too_many_caps,
)


class ValidatorTests(TestCase):
    def test_validate_not_allcaps(self):
        valid = ("ZAM", "Zam", "zim Zam zum", "McCoy", "鋭郎", "鋭郎 三好", "O'Hara", "O’Timmins")
        invalid = ("ZAMENHOF", "MC COY")
        for value in valid:
            self.assertEqual(validate_not_all_caps(value), None)
        for value in invalid:
            self.assertRaises(ValidationError, validate_not_all_caps, value)

    def test_validate_not_toomanycaps(self):
        valid = ("ZAM", "Zam", "zim Zam zum", "McCoy", "鋭郎", "鋭郎 三好", "O'Hara", "O’Timmins")
        invalid = ("ZAMENHOF", "ZAm", "mcCOY", "mc COY")
        for value in valid:
            self.assertEqual(validate_not_too_many_caps(value), None)
        for value in invalid:
            self.assertRaises(ValidationError, validate_not_too_many_caps, value)
