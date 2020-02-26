from typing import NamedTuple

from django.conf import settings
from django.test import TestCase, tag

from core.utils import camel_case_split, sort_by
from hosting.utils import (
    split, title_with_particule, value_without_invalid_marker,
)


@tag('utils')
class UtilityFunctionsTests(TestCase):
    def test_camel_case_split(self):
        test_data = (
            ("title", ["title"]),
            ("tiTle", ["ti", "Tle"]),
            ("titlE", ["titl", "E"]),
            ("TITLE", ["TITLE"]),
            ("TItLe", ["T", "It", "Le"]),
            ("TItLE", ["T", "It", "LE"]),
            ("ACamelCaseIsOftenUsedForVariables", ["A", "Camel", "Case", "Is", "Often", "Used", "For", "Variables"]),
            ("an tAlbanach", ["an t", "Albanach"]),
        )
        for camel_case_value, expected_value in test_data:
            with self.subTest(value=camel_case_value):
                self.assertEqual(camel_case_split(camel_case_value), expected_value)

    def test_title_with_particule_and_builtin_list(self):
        test_data = (
            ("title", "Title"),
            ("TITLE", "Title"),
            ("tiTle", "Title"),
            ("title one", "Title One"),
            ("TITLE TWO", "Title Two"),
            ("ibn Khaldun", "Ibn Khaldun"),
            ("nasir al-din al-tusi", "Nasir Al-Din Al-Tusi"),
            ("d'artagnan", "D'Artagnan"),
            ("D'artagnan", "D'Artagnan"),
            ("d\"artagnan", "D\"Artagnan"),
            ("D\"artagnaN", "D\"Artagnan"),
            ("van artagnan", "van Artagnan"),
            ("del artagnaN", "del Artagnan"),
            ("Af-arTagnan", "af-Artagnan"),
            ("d.arta.gnan", "D.Arta.Gnan"),
        )
        for title, expected_value in test_data:
            with self.subTest(title=title):
                self.assertEquals(title_with_particule(title), expected_value)

    def test_title_with_particule_and_provided_list(self):
        test_data = (
            ("abu zayd ibn khaldun al-hadrami", "Abu Zayd ibn Khaldun al-Hadrami"),
            ("nasir al-din al-tusi", "Nasir al-Din al-Tusi"),
            ("d'artagnan", "D'Artagnan"),
            ("van artagnan", "Van Artagnan"),
            ("del artagnan", "Del Artagnan"),
            ("Af-ARTAGNAN", "Af-Artagnan"),
        )
        for title, expected_value in test_data:
            with self.subTest(title=title):
                self.assertEquals(title_with_particule(title, ["ibn", "al"]), expected_value)

    def test_split_util(self):
        test_data = (
            ("ibn Khaldun", ["ibn", "Khaldun"]),
            ("ibn_Khaldun", ["ibn_Khaldun"]),
            ("ibn-Khaldun", ["ibn", "Khaldun"]),
            ("ibn.Khaldun", ["ibn", "Khaldun"]),
            ("ibn'Khaldun", ["ibn", "Khaldun"]),
            ("ibn5Khaldun", ["ibn5Khaldun"]),
        )
        for original_value, expected_value in test_data:
            with self.subTest(value=original_value):
                self.assertEquals(split(original_value), expected_value)

    def test_value_without_invalid_marker(self):
        test_data = (
            ("user@mail.com", "user@mail.com"),
            ("user_{}@mail.com".format(settings.INVALID_PREFIX), "user_{}@mail.com".format(settings.INVALID_PREFIX)),
            ("user@mail.com_{}".format(settings.INVALID_PREFIX), "user@mail.com_{}".format(settings.INVALID_PREFIX)),
            ("{0}{0}user".format(settings.INVALID_PREFIX), "{}user".format(settings.INVALID_PREFIX)),
            ("{0}user{0}".format(settings.INVALID_PREFIX), "user{}".format(settings.INVALID_PREFIX)),
            ("{}user@not--mail".format(settings.INVALID_PREFIX), "user@not--mail"),
        )
        for original_value, expected_value in test_data:
            with self.subTest(value=original_value):
                self.assertEqual(value_without_invalid_marker(original_value), expected_value)

    def test_sort_by_simple(self):
        Country = NamedTuple("Country", [("code", str), ("name", str)])
        countries = zw, cn, ca = Country("ZW", "Zimbabvo"), Country("CN", "Ĉinio"), Country("CA", "Kanado")
        expected = [cn, ca, zw]

        self.assertEqual(sort_by(["name"], countries), expected)

    def test_sort_by_nested(self):
        Person = NamedTuple("Person", [("name", str)])
        House = NamedTuple("House", [("city", str), ("country", str), ("owner", Person)])
        houses = wta, ptb, pfa, pfb, pta = (
            House("Pawnee", "Texas", Person("A")),
            House("Paris", "Texas", Person("B")),
            House("Paris", "France", Person("A")),
            House("Paris", "France", Person("B")),
            House("Paris", "Texas", Person("A")),
        )
        expected = [pfa, pfb, pta, ptb, wta]

        self.assertEqual(sort_by(["owner.name", "city", "country"], houses), expected)
