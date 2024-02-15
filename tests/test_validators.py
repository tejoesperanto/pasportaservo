from datetime import date, timedelta
from io import BytesIO
from unittest.mock import Mock, PropertyMock, patch

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db.models import CharField, Model
from django.forms import ModelForm
from django.test import TestCase, modify_settings, override_settings, tag

from factory import Faker

from hosting.validators import (
    AccountAttributesSimilarityValidator, TooFarPastValidator,
    TooNearPastValidator, client_side_validated, validate_image,
    validate_latin, validate_no_digit, validate_not_all_caps,
    validate_not_in_future, validate_not_too_many_caps, validate_size,
)

from .assertions import AdditionalAsserts
from .factories import GenderFactory, UserFactory


@tag('validators')
class ValidatorsTests(AdditionalAsserts, TestCase):
    def test_validate_not_all_caps(self):
        valid = [
            "ZAM", "ZaM", "Zam", "zim Zam Zum", "McCoy", "O'Hara", "O’Timmins",
            "鋭郎", "鋭郎 三好", "An-Nāṣir Ṣalāḥ ad-Dīn", "الناصر صلاح الدين", "!@#'%", "(B)"
        ]
        invalid = {"ZAMENHOF": "Zamenhof", "MC COY": "Mc Coy", "O’MA'HONY": "O’Ma'Hony"}
        for value in valid:
            with self.subTest(valid_value=value):
                with self.assertNotRaises(ValidationError):
                    validate_not_all_caps(value)
        for value in invalid:
            with self.subTest(invalid_value=value):
                with self.assertRaises(ValidationError) as cm:
                    validate_not_all_caps(value)
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(
                        next(iter(cm.exception)),
                        f"Today is not CapsLock day. Please try with '{invalid[value]}'."
                    )
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertStartsWith(
                        next(iter(cm.exception)),
                        "La CapsLock-tago ne estas hodiaŭ."
                    )

    def test_validate_not_too_many_caps(self):
        valid = [
            "ZAM", "Zam", "AZam", "zim Zam Zum", "McCoy", "O'Hara", "O’Timmins",
            "(鋭之進郎)", "鋭郎 三好", "AnNāṣir Ṣalāḥ AdDīn", "الناصر صلاح الدين", "DelaCruz", "!@#'%"
        ]
        msg_all_caps = {
            'en': "Today is not CapsLock day",
            'eo': "La CapsLock-tago ne estas hodiaŭ",
        }
        msg_many_caps = {
            'en': "It seems there are too many uppercase letters",
            'eo': "Ŝajnas ke estas tro da majuskloj",
        }
        invalid = {
            "ZAMENHOF": ("Zamenhof", msg_all_caps),
            "ZAm": ("Zam", msg_many_caps),
            "LAZAM": ("Lazam", msg_all_caps),
            "mcCOY": ("Mccoy", msg_many_caps),
            "mc COY": ("Mc Coy", msg_many_caps),
            "DeLaCruz": ("Delacruz", msg_many_caps),
            "deL VarSoviA": ("del Varsovia", msg_many_caps),
        }
        for value in valid:
            with self.subTest(valid_value=value):
                with self.assertNotRaises(ValidationError):
                    validate_not_too_many_caps(value)
        for value, (correct_value, expected_error) in invalid.items():
            with self.subTest(invalid_value=value):
                with self.assertRaises(ValidationError) as cm:
                    validate_not_too_many_caps(value)
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(
                        next(iter(cm.exception)),
                        f"{expected_error['en']}. Please try with '{correct_value}'."
                    )
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertStartsWith(
                        next(iter(cm.exception)),
                        expected_error['eo']
                    )

    def test_validate_no_digit(self):
        valid = ["VARSOVIO", " Varšava ", "\tװאַרשע", "ვარშავა", "وارسو:٢٢", "二十二", "²₂WawA", "!@#'%"]
        valid.append("𝟷𝟾𝟻𝟿–𝟙𝟡𝟙𝟟")  # These digits are from the Math Alphanumeric Symbols Unicode block.
        invalid = ["VARS0", " Varsóv1a ", "\n\r\tLe3T\b\a"]
        for value in valid:
            with self.subTest(valid_value=value):
                with self.assertNotRaises(ValidationError):
                    validate_no_digit(value)
        for value in invalid:
            with self.subTest(invalid_value=value):
                with self.assertRaises(ValidationError) as cm:
                    validate_no_digit(value)
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(next(iter(cm.exception)), "Digits are not allowed.")
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertEqual(
                        next(iter(cm.exception)),
                        "Ciferoj ne estas permesitaj en tiu ĉi kampo."
                    )
        # Verify that client-side constraint is properly defined.
        self.assertTrue(hasattr(validate_no_digit, 'constraint'))
        self.assertIn('pattern', validate_no_digit.constraint)

    def test_validate_latin(self):
        basic_strings = ["Zam", "زامنهوف", "柴門霍夫"]
        valid_prefix = [
            "L", "L.", "la-", "Ł", "Ĉ", "Æ", "Ø", "Ý", "Þ", "ð", "ÿ", "ď", "œ", "ß", "ſ", "Ə",
            "Ƙ", "ƶ", "ƿ", "Ǚ", "Ș", "ȵ", "ɢ", "ʟ", "Ḝ", "ṥ", "ỿ", "ͩA", "̃Q", "̴J", "I̴", "ɀ",
        ]
        invalid_prefix = [
            "!", "1", "像", "ל", "ზ", "ᴌ", "ᴔ", "ʳ", "ʶ", "ᴳ", "ᶍ", "ᶭ", "ᶽ", "Å", "Ⱶ", "Ꜯ", "Ꝕ",
            "Ꝙ", "Ꞟ", "ꭙ", "ﬃ", "ⅻ", "ℛ", "℉", "𝐙", "𝑦", "𝓻", "𝔚", "𝕏", "𝖍", "𝘴", "Ｌ", "ｊ",
        ]
        for base in basic_strings:
            for value in valid_prefix:
                with self.subTest(valid_value=value + base):
                    with self.assertNotRaises(ValidationError):
                        validate_latin(value + base)
            for value in invalid_prefix:
                with self.subTest(invalid_value=value + base):
                    with self.assertRaises(ValidationError) as cm:
                        validate_latin(value + base)
                    with override_settings(LANGUAGE_CODE='en'):
                        self.assertStartsWith(
                            next(iter(cm.exception)),
                            "Please provide this data in Latin characters"
                        )
                    with override_settings(LANGUAGE_CODE='eo'):
                        self.assertStartsWith(
                            next(iter(cm.exception)),
                            "Bonvole indiku tiun ĉi informon per latinaj literoj"
                        )
        # Verify that client-side constraint is properly defined.
        self.assertTrue(hasattr(validate_latin, 'constraint'))
        self.assertIn('pattern', validate_latin.constraint)

    def test_validate_image_type(self):
        faker = Faker._get_faker()
        data = BytesIO(faker.binary(length=10))
        data.name = faker.file_name(category='image')
        class DummyField: pass       # noqa: E701
        test_content = DummyField()  # Mocking the Django's ImageField.

        with self.assertNotRaises(ValidationError):
            # A field with no underlying file is expected to pass the validation.
            validate_image(test_content)
            type(test_content).file = PropertyMock(side_effect=FileNotFoundError)
            validate_image(test_content)
            del type(test_content).file  # Clear the property mock for further testing.
            # A field with file of unknown content type is expected to pass the validation.
            test_content.file = data
            validate_image(test_content)
            # A field with file of content type 'image' is expected to pass the validation.
            data.content_type = faker.mime_type(category='image')
            validate_image(test_content)

        # A field with file of unsupported content type is expected to fail validation.
        for category in ['application', 'audio', 'message', 'model', 'multipart', 'text', 'video']:
            data.content_type = faker.mime_type(category=category)
            with self.subTest(content_type=data.content_type):
                with self.assertRaises(ValidationError) as cm:
                    validate_image(test_content)
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(next(iter(cm.exception)), "File type is not supported.")
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertEqual(next(iter(cm.exception)), "Dosiertipo ne akceptebla.")

    def test_validate_image_size(self):
        faker = Faker._get_faker()
        class DummyField: pass       # noqa: E701
        test_content = DummyField()  # Mocking the Django's ImageField.

        def prep_data(length):
            data = BytesIO(faker.binary(length=length))
            data.name = faker.file_name(category='image')
            data.content_type = faker.mime_type(category='image')
            data.size = length
            return data

        # A field with no underlying file is expected to pass the validation.
        with self.assertNotRaises(ValidationError):
            type(test_content).file = PropertyMock(side_effect=FileNotFoundError)
            validate_size(test_content)
            del type(test_content).file  # Clear the property mock for further testing.

        # File size lesser than or equal to 100 kB is expected to be accepted.
        for test_length in (10, 1024, 102400):
            test_content.file = prep_data(test_length)
            with self.subTest(size=test_length):
                with self.assertNotRaises(ValidationError):
                    validate_size(test_content)

        # File size larger than 100 kB is expected to fail the validation.
        for test_length in (102402, 102502):
            test_content.file = prep_data(test_length)
            with self.subTest(size=test_length):
                with self.assertRaises(ValidationError) as cm:
                    validate_size(test_content)
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertStartsWith(
                        next(iter(cm.exception)),
                        "Please keep file size under 100.0 KB."
                    )
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertStartsWith(
                        next(iter(cm.exception)),
                        "Bv. certigu ke dosiergrando estas sub 100,0 KB."
                    )

        # Verify that client-side constraint is properly defined.
        self.assertTrue(hasattr(validate_size, 'constraint'))
        self.assertIn('maxlength', validate_size.constraint)

    def test_validate_not_in_future(self):
        for delta in (365, 1, 0):
            date_value = date.today() - timedelta(days=delta)
            with self.subTest(date_value=date_value):
                with self.assertNotRaises(ValidationError):
                    validate_not_in_future(date_value)
        for delta in (1, 7, 365):
            date_value = date.today() + timedelta(days=delta)
            with self.subTest(date_value=date_value):
                with self.assertRaises(ValidationError) as cm:
                    validate_not_in_future(date_value)
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(
                        next(iter(cm.exception)),
                        f"Ensure this value is less than or equal to {date.today():%Y-%m-%d}."
                    )
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertEqual(
                        next(iter(cm.exception)),
                        f"Certigu ke ĉi tiu valoro estas malpli ol aŭ egala al {date.today():%Y-%m-%d}."
                    )

    def test_too_far_past_validator(self):
        validator10 = TooFarPastValidator(10)
        self.assertNotEqual(validator10, None)
        self.assertNotEqual(validator10, object())
        self.assertNotEqual(validator10, TooNearPastValidator(10))
        self.assertNotEqual(validator10, 10)
        self.assertEqual(validator10, validator10)
        self.assertEqual(validator10, TooFarPastValidator(10.0))

        faker = Faker._get_faker()
        with patch('hosting.validators.date', Mock(today=Mock(return_value=date(2024, 2, 29)))):
            for date_value in (faker.date_between_dates(date_start=date(2014, 3, 2), date_end=date(2024, 2, 28)),
                               date(2014, 2, 28),
                               date(2014, 3, 1),
                               date(2024, 2, 29),
                               faker.date_between_dates(date_start=date(2024, 3, 1), date_end=date(2030, 1, 15))):
                with self.subTest(date_value=date_value):
                    with self.assertNotRaises(ValidationError):
                        validator10(date_value)

            for date_value in (faker.date_between_dates(date_start=date(2000, 1, 1), date_end=date(2013, 12, 1)),
                               date(2014, 1, 2),
                               date(2014, 2, 27)):
                with self.subTest(date_value=date_value):
                    with self.assertRaises(ValidationError) as cm:
                        validator10(date_value)
                    with override_settings(LANGUAGE_CODE='en'):
                        self.assertEqual(
                            next(iter(cm.exception)),
                            "Ensure this value is greater than or equal to 2014-02-28."
                        )
                    with override_settings(LANGUAGE_CODE='eo'):
                        self.assertEqual(
                            next(iter(cm.exception)),
                            "Certigu ke ĉi tiu valoro estas pli ol aŭ egala al 2014-02-28."
                        )

    def test_too_near_past_validator(self):
        validator5 = TooNearPastValidator(5)
        self.assertNotEqual(validator5, None)
        self.assertNotEqual(validator5, object())
        self.assertNotEqual(validator5, TooFarPastValidator(5))
        self.assertNotEqual(validator5, 5)
        self.assertEqual(validator5, validator5)
        self.assertEqual(validator5, TooNearPastValidator(5.0))

        faker = Faker._get_faker()
        with patch('hosting.validators.date', Mock(today=Mock(return_value=date(2024, 2, 29)))):
            for date_value in (faker.date_between_dates(date_start=date(2000, 2, 1), date_end=date(2019, 2, 27)),
                               date(2019, 2, 28)):
                with self.subTest(date_value=date_value):
                    with self.assertNotRaises(ValidationError):
                        validator5(date_value)

            for date_value in (faker.date_between_dates(date_start=date(2019, 3, 1), date_end=date(2024, 2, 28)),
                               date(2019, 3, 1),
                               date(2024, 2, 28),
                               date(2024, 2, 29),
                               faker.date_between_dates(date_start=date(2024, 3, 1), date_end=date(2030, 1, 15))):
                with self.subTest(date_value=date_value):
                    with self.assertRaises(ValidationError) as cm:
                        validator5(date_value)
                    with override_settings(LANGUAGE_CODE='en'):
                        self.assertEqual(
                            next(iter(cm.exception)),
                            "Ensure this value is less than or equal to 2019-02-28."
                        )
                    with override_settings(LANGUAGE_CODE='eo'):
                        self.assertEqual(
                            next(iter(cm.exception)),
                            "Certigu ke ĉi tiu valoro estas malpli ol aŭ egala al 2019-02-28."
                        )


@tag('validators')
class ClientSideValidationSetupTests(AdditionalAsserts, TestCase):
    @classmethod
    @modify_settings(INSTALLED_APPS={
        'append': 'tests.test_validators',
    })
    def setUpClass(cls):
        super().setUpClass()

        def validate_alpha():
            pass
        validate_alpha.constraint = ('maxlength', 10)
        validate_alpha.message = "Length up to 10"

        def validate_beta():
            pass
        validate_beta.constraint = ('length', 2, 12)

        def validate_gamma():
            pass
        validate_gamma.constraint = {'pattern': '^Xyz', 'minlength': 6}

        def validate_delta():
            pass
        validate_delta.constraint = {'pattern': '[a-f]{6}'}

        def validate_epsilon():
            pass

        def validate_wau():
            pass
        validate_wau.constraint = ['step', (5, 7)]

        class Dummy(Model):
            aa = CharField(validators=[validate_alpha])
            bb = CharField(validators=[validate_beta])
            cc = CharField(validators=[validate_gamma])
            dd = CharField(validators=[validate_delta])
            ee = CharField(validators=[validate_epsilon])
            ff = CharField(validators=[validate_wau])
        cls.DummyModel = Dummy

    def test_valid_tuple_constraint(self):
        @client_side_validated
        class DummyForm(ModelForm):
            class Meta:
                model = self.DummyModel
                fields = ['aa', 'ee']

        with self.assertNotRaises(ImproperlyConfigured):
            form = DummyForm()
        self.assertIn('maxlength', form.fields['aa'].widget.attrs)
        self.assertEqual(form.fields['aa'].widget.attrs['maxlength'], 10)
        self.assertIn('data-error-maxlength', form.fields['aa'].widget.attrs)

    def test_valid_dict_constraint(self):
        @client_side_validated
        class DummyForm(ModelForm):
            class Meta:
                model = self.DummyModel
                fields = ['ee', 'dd']

        with self.assertNotRaises(ImproperlyConfigured):
            form = DummyForm()
        self.assertIn('pattern', form.fields['dd'].widget.attrs)
        self.assertEqual(form.fields['dd'].widget.attrs['pattern'], '[a-f]{6}')
        self.assertNotIn('data-error-pattern', form.fields['dd'].widget.attrs)

    def test_invalid_constraint(self):
        @client_side_validated
        class ManyValuesForm(ModelForm):
            class Meta:
                model = self.DummyModel
                fields = ['ee', 'bb']

        with self.assertRaises(ImproperlyConfigured) as cm:
            ManyValuesForm()
        self.assertSurrounding(
            str(cm.exception),
            "Client-side constraint ", " must consist of name and value only."
        )

        @client_side_validated
        class ManyKeysForm(ModelForm):
            class Meta:
                model = self.DummyModel
                fields = ['cc', 'ee']

        with self.assertRaises(ImproperlyConfigured) as cm:
            ManyKeysForm()
        self.assertSurrounding(
            str(cm.exception),
            "Client-side constraint ", " must consist of name and value only."
        )

    def test_unexpected_constraint(self):
        @client_side_validated
        class DummyForm(ModelForm):
            class Meta:
                model = self.DummyModel
                fields = ['ff']

        with self.assertNotRaises(ImproperlyConfigured):
            form = DummyForm()
        self.assertIn('step', form.fields['ff'].widget.attrs)
        self.assertEqual(form.fields['ff'].widget.attrs['step'], (5, 7))
        self.assertNotIn('data-error-step', form.fields['ff'].widget.attrs)


@tag('validators')
class AccountAttributesSimilarityValidatorTests(AdditionalAsserts, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.validator_default = AccountAttributesSimilarityValidator()
        cls.validator_default.tag = "default"
        cls.validator_all = AccountAttributesSimilarityValidator(0.0)
        cls.validator_all.tag = "all"
        cls.validator_exact = AccountAttributesSimilarityValidator(1.0)
        cls.validator_exact.tag = "exact"
        cls.validator_none = AccountAttributesSimilarityValidator(1.1)
        cls.validator_none.tag = "none"
        cls.validators = [
            cls.validator_default,
            cls.validator_all,
            cls.validator_exact,
            cls.validator_none,
        ]

    def test_operators(self):
        self.assertNotEqual(self.validator_default, None)
        self.assertNotEqual(self.validator_default, object())
        self.assertNotEqual(self.validator_default, 0.70)
        self.assertEqual(self.validator_default, self.validator_default)
        self.assertEqual(self.validator_default, AccountAttributesSimilarityValidator(70 / 100))

    def _get_spec(self, validator):
        return {'validator_tag': validator.tag, 'allowed_similarity': validator.max_similarity}

    def test_no_user(self):
        # When no user object is provided, all validators are expected to succeed.
        for v in self.validators:
            with self.subTest(**self._get_spec(v)):
                self.assertNotRaises(ValidationError, lambda v=v: v("dRakuJo"))

    def test_validation(self):
        test_config = [
            {
                'user_data': {'username': "drake_jennifer", 'email': "", 'profile': None},
                'field': 'username',
                'violations': {'en': "username", 'eo': "salutnomo"},
            }, {
                'user_data': {'email': "drake_jennifer@mail.edu", 'profile': None},
                'field': 'email',
                'violations': {'en': "email address", 'eo': "retpoŝta adreso"},
            }, {
                'user_data': {'email': "INVALID_84+refinnejekard@mail.edu", 'profile': None},
                'field': 'email (invalid)',
                'violations': {'en': "email address", 'eo': "retpoŝta adreso"},
            }, {
                'user_data': {
                    'email': "",
                    'profile__first_name': "Ardinej",
                    'profile__last_name': "",
                    'profile__email': "",
                },
                'field': 'first_name',
                'violations': {'en': "first name", 'eo': "persona nomo"},
            }, {
                'user_data': {
                    'email': "",
                    'profile__first_name': "",
                    'profile__last_name': "Drakennir",
                    'profile__email': "",
                },
                'field': 'last_name',
                'violations': {'en': "last name", 'eo': "familia nomo"},
            }, {
                'user_data': {
                    'email': "",
                    'profile__first_name': "",
                    'profile__last_name': "",
                    'profile__email': "jen@rinnekard.io",
                },
                'field': 'profile_email',
                'violations': {'en': "public email", 'eo': "publika retpoŝta adreso"},
            }, {
                'user_data': {
                    'email': "",
                    'profile__first_name': "",
                    'profile__last_name': "",
                    'profile__email': "INVALID_Drake_Jenni17@hotmail.com",
                },
                'field': 'profile_email (invalid)',
                'violations': {'en': "public email", 'eo': "publika retpoŝta adreso"},
            }, {
                'user_data': {
                    'username': "Drake_Jen",
                    'email': "jenni@drake.com",
                    'profile__first_name': "Jennifer",
                    'profile__last_name': "Drakennir",
                    'profile__email': "",
                },
                'field': 'multiple',
                'violations': {
                    'en': "username, email address, first name, last name",
                    'eo': "salutnomo, retpoŝta adreso, persona nomo, familia nomo",
                },
            },
        ]

        for test_data in test_config:
            user = UserFactory(**test_data['user_data'])
            if 'username' not in test_data['user_data']:
                user.username = ""
            with self.subTest(field=test_data['field']):
                for v in [self.validator_default, self.validator_all]:
                    with self.subTest(**self._get_spec(v)):
                        with self.assertRaises(ValidationError) as cm:
                            v("Jennidrake", user)
                        with override_settings(LANGUAGE_CODE='en'):
                            self.assertEqual(
                                next(iter(cm.exception)),
                                f"The password is too similar to the {test_data['violations']['en']}."
                            )
                        with override_settings(LANGUAGE_CODE='eo'):
                            self.assertEqual(
                                next(iter(cm.exception)),
                                f"La pasvorto estas tro simila al la {test_data['violations']['eo']}."
                            )
                for v in [self.validator_exact, self.validator_none]:
                    with self.subTest(**self._get_spec(v)):
                        self.assertNotRaises(ValidationError, lambda v=v: v("Jennidrake", user))

    def test_extreme_validation(self):
        user = UserFactory(invalid_email=True, profile__last_name="Dragons Here", profile__with_email=True)
        test_config = [
            {
                'validator': self.validator_all,
                # The "catch all" validator with similarity 0 is expected to reject all values.
                'violations': {
                    'en': "username, email address, first name, last name, public email",
                    'eo': "salutnomo, retpoŝta adreso, persona nomo, familia nomo, publika retpoŝta adreso",
                },
            }, {
                'validator': self.validator_exact,
                # The "exact value" validator with similarity 1 is expected to reject only strictly equal values.
                'violations': {
                    'en': "last name",
                    'eo': "familia nomo",
                }
            }
        ]

        for test_data in test_config:
            with self.subTest(**self._get_spec(test_data['validator'])):
                with self.assertRaises(ValidationError) as cm:
                    test_data['validator']("ereh snogard", user)
                with override_settings(LANGUAGE_CODE='en'):
                    self.assertEqual(
                        next(iter(cm.exception)),
                        f"The password is too similar to the {test_data['violations']['en']}."
                    )
                with override_settings(LANGUAGE_CODE='eo'):
                    self.assertEqual(
                        next(iter(cm.exception)),
                        f"La pasvorto estas tro simila al la {test_data['violations']['eo']}."
                    )

    @patch('hosting.validators.SequenceMatcher')
    def test_overly_long_value(self, mock_matcher):
        user = UserFactory(
            username="AbAb", email="a@b.co",
            profile__first_name="Ab Ba", profile__last_name="Ba")
        test_value = "Ab" * 300
        for v in self.validators:
            with self.subTest(**self._get_spec(v)):
                if v is not self.validator_all:
                    self.assertNotRaises(ValidationError, lambda v=v: v(test_value, user))
                else:
                    self.assertRaises(ValidationError, lambda v=v: v(test_value, user))
                mock_matcher.assert_not_called()
                mock_matcher.reset_mock()

    def test_non_validation(self):
        # For profile attributes not inspected by the validators, no violation is expected.
        gender = GenderFactory(name="DraGonS HeRe!")
        user = UserFactory(
            email="", profile__first_name="", profile__last_name="", profile__email="",
            profile__description="Dragons here!", profile__gender=gender)
        user.username = ""
        with self.subTest(attributes=('description', 'gender')):
            for v in self.validators:
                for test_value in ["dragons here!", "!ereh snogard"]:
                    with self.subTest(**self._get_spec(v), test_value=test_value):
                        self.assertNotRaises(
                            ValidationError,
                            lambda v=v, value=test_value: v(value, user)
                        )
