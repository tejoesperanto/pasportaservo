import copy
import logging
import operator
import random
from typing import NamedTuple, cast
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.contrib.gis.geos import Point as GeoPoint
from django.core import mail
from django.test import TestCase, override_settings, tag
from django.utils.functional import SimpleLazyObject, lazy, lazystr

from anymail.message import AnymailMessage
from anymail.utils import UNSET
from factory import Faker
from geocoder.opencage import OpenCageQuery, OpenCageResult
from requests.exceptions import (
    ConnectionError as HTTPConnectionError, HTTPError,
)

from core.utils import (
    camel_case_split, is_password_compromised,
    join_lazy, send_mass_html_mail, sort_by, split,
)
from hosting.countries import countries_with_mandatory_region
from hosting.gravatar import email_to_gravatar
from hosting.utils import (
    RenameAndPrefixAvatar, emulate_geocode_country, geocode,
    geocode_city, title_with_particule, value_without_invalid_marker,
)
from links.utils import create_unique_url
from maps import data as geodata
from maps.utils import bufferize_country_boundaries

from .assertions import AdditionalAsserts
from .factories import ProfileFactory, ProfileSansAccountFactory


@tag('utils')
class UtilityFunctionsTests(AdditionalAsserts, TestCase):
    def test_camel_case_split(self):
        test_data = (
            ("title", ["title"]),
            ("tiTle", ["ti", "Tle"]),
            ("titlE", ["titl", "E"]),
            ("TITLE", ["TITLE"]),
            ("TItLe", ["T", "It", "Le"]),
            ("TItLE", ["T", "It", "LE"]),
            ("ACamelCaseIsOftenUsedForVariables",
             ["A", "Camel", "Case", "Is", "Often", "Used", "For", "Variables"]),
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
            ("", ""),
            (None, None),
        )
        for title, expected_value in test_data:
            with self.subTest(title=title):
                self.assertEqual(title_with_particule(title), expected_value)

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
                self.assertEqual(title_with_particule(title, ["ibn", "al"]), expected_value)

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
                self.assertEqual(split(original_value), expected_value)

    def test_value_without_invalid_marker(self):
        test_data = (
            ("user@mail.com", "user@mail.com"),
            (f"user_{settings.INVALID_PREFIX}@mail.com", f"user_{settings.INVALID_PREFIX}@mail.com"),
            (f"user@mail.com_{settings.INVALID_PREFIX}", f"user@mail.com_{settings.INVALID_PREFIX}"),
            ("{0}{0}user".format(settings.INVALID_PREFIX), f"{settings.INVALID_PREFIX}user"),
            ("{0}user{0}".format(settings.INVALID_PREFIX), f"user{settings.INVALID_PREFIX}"),
            (f"{settings.INVALID_PREFIX}user@not--mail", "user@not--mail"),
        )
        self.assertNotEqual(settings.INVALID_PREFIX, "")
        for original_value, expected_value in test_data:
            with self.subTest(value=original_value):
                self.assertEqual(value_without_invalid_marker(original_value), expected_value)

    def test_sort_by_simple(self):
        Country = NamedTuple('Country', [('code', str), ('name', str)])
        countries = zw, cn, ca = Country("ZW", "Zimbabvo"), Country("CN", "Ĉinio"), Country("CA", "Kanado")
        expected = [cn, ca, zw]

        self.assertEqual(sort_by(['name'], countries), expected)

    def test_sort_by_nested(self):
        Person = NamedTuple('Person', [('name', str)])
        House = NamedTuple('House', [('city', str), ('country', str), ('owner', Person)])
        houses = wta, ptb, pfa, pfb, pta = (
            House("Pawnee", "Texas", Person("A")),
            House("Paris", "Texas", Person("B")),
            House("Paris", "France", Person("A")),
            House("Paris", "France", Person("B")),
            House("Paris", "Texas", Person("A")),
        )
        expected = [pfa, pfb, pta, ptb, wta]

        self.assertEqual(sort_by(['owner.name', 'city', 'country'], houses), expected)

    def test_join_lazy(self):
        test_data = {
            'sep': (", ", lazystr(", ")),
            'items': (
                lambda: ["aa", "bb", "cc"],
                lambda: [lazystr("aa"), "bb", lazystr("cc")],
                lazy(lambda: ["aa", lazystr("bb"), "cc"], list),
            ),
        }
        for sep, i_sep, items, j_items in [(s, i, l, j)
                                           for i, s in enumerate(test_data['sep'], start=1)
                                           for j, l in enumerate(test_data['items'], start=1)]:
            with self.subTest(sep=i_sep, list=j_items):
                joined = join_lazy(sep, items())
                self.assertIn('_proxy____cast', dir(joined))
                self.assertEqual(str(joined), "aa, bb, cc")

    def test_simplelazyobject_patch(self):
        # The patched Django's SimpleLazyObject is expected to
        # support integers and arithmetic operations.
        test_data = (
            ('isgt', operator.gt, 2),
            ('iseq', operator.eq, 2),
            ('cast', int, 1),
            ('sum',  operator.add, 2),
            ('mult', operator.mul, 2),
        )
        for op_tag, operation, num_params in test_data:
            x = SimpleLazyObject(lambda: 123)
            y = copy.deepcopy(x)
            # The lazy object is expected to be able to compare
            # to, be added to, and be multiplied by a numeric value.
            # Also an explicit conversion to integer is expected to
            # raise no error.
            with self.subTest(op=op_tag, obj='original'):
                with self.assertNotRaises(TypeError):
                    if num_params == 1:
                        operation(x)
                    else:
                        operation(x, 50)
                self.assertIs(type(x), SimpleLazyObject)
                self.assertIsNot(type(x), int)
            # A copy of the lazy object (done prior to evaluation
            # of the value) is expected to behave similarly.
            with self.subTest(op=op_tag, obj='copy'):
                with self.assertNotRaises(TypeError):
                    if num_params == 1:
                        operation(y)
                    else:
                        operation(y, 150)
                self.assertIs(type(y), SimpleLazyObject)
                self.assertIsNot(type(y), int)
            # A copy of the lazy object, done after evaluation of
            # the value, is expected to be a real integer and
            # support the anticipated arithmetic operations as well
            # as comparisons or conversions.
            z = copy.copy(x)
            with self.subTest(op=op_tag, obj='copy after eval'):
                with self.assertNotRaises(TypeError):
                    if num_params == 1:
                        operation(z)
                    else:
                        operation(z, 250)
                self.assertIs(type(z), int)
                self.assertIsNot(type(z), SimpleLazyObject)

    def test_email_to_gravatar(self):
        test_data = (
            {'fallback': None, 'size': 250},
            {'fallback': '', 'size': None},
            {'fallback': '', 'size': 5000},
            {'fallback': '404', 'size': None},
            {'fallback': '404', 'size': 7500},
        )
        for params in test_data:
            with self.subTest(extra_params=params):
                url = email_to_gravatar("ehxo.sxangxo@cxiu.jxauxde.org", **params)
                self.assertStartsWith(url, "https://")
                self.assertIn("gravatar.com", url)
                self.assertIn("dcfd20df1a72567cbe06c4bce058f513", url)
                self.assertNotIn("None", url)

    @tag('avatar')
    def test_rename_avatar(self):
        util = RenameAndPrefixAvatar('/storage/')
        # Avatar's path for a non-saved profile linked to a user
        # is expected to include the user ID prefixed by 'u'.
        profile = ProfileFactory.build()
        profile.user.save()
        with self.subTest(profile=profile.pk, user=profile.user.pk):
            path = util(profile, "new_image.2021.Jpeg")
            self.assertRegex(path, fr"^/storage/picture-u{profile.user.id}_[0-9a-f]{{8}}\.jpeg$")
        # Avatar's path for a non-saved profile without a user
        # is expected to include just the indicator 'x'.
        profile = ProfileSansAccountFactory.build()
        with self.subTest(profile=profile.pk, user=profile.user):
            path = util(profile, "Screenshot-2018.09.26_cropped+mirrored.PnG")
            self.assertRegex(path, r"^/storage/picture-x[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\.png$")
        # Avatar's path for a saved profile linked to a user
        # is expected to include the profile ID prefixed by 'p'.
        profile = ProfileFactory()
        with self.subTest(profile=profile.pk, user=profile.user.pk):
            path = util(profile, "overly long and overtly descriptive name for a file.BMP")
            self.assertRegex(path, fr"^/storage/picture-p{profile.id}_[0-9a-f]{{8}}\.bmp$")
        # Avatar's path for a saved profile without a user
        # is expected to include the profile ID prefixed by 'p'.
        profile = ProfileSansAccountFactory()
        with self.subTest(profile=profile.pk, user=profile.user):
            path = util(profile, "invalid>filename<attempt|.tiffany")
            self.assertRegex(path, fr"^/storage/picture-p{profile.id}_[0-9a-f]{{8}}\.tiffany$")

    @patch('core.utils.requests.get')
    def test_is_password_compromised(self, mock_get):
        test_data = (
            ("NoConnection", 500, (None, None), HTTPConnectionError),
            ("ServerError!", 500, (None, None), None),
            ("esperanto", 200, (True, 17000), None),
            ("esperanto1234", 200, (True, 1), None),  # appears in the list with count 1
            ("esperanto567", 200, (False, 0), None),  # appears in the list with count 0
            ("Zamenhof1887", 200, (False, 0), None),  # does not appear in the list
        )
        hashes = (
            "37A46DA96ED9243AA3C0F328E59F7230AC7:0\n"
            "D5F41AA14D03396500BC4B71F442A458070:0\n"
            "CCCE0D1821374F822B7B141C869F056D01E:0\n"
            "455901A589F33D5EC929257DAC716133E29:17000\n"
            "467E2DDDD648F54A9F1B20CA834697CF604:0\n"
            "ABBECC310317257B8FBA5D05BFDC1CE5B0D:0\n"
            "0C926B6A8B4850866E3E2257BA3D06DDBDA:0\n"
            "5679F473CE6B5ED41A00166519D09808CD5:1\n"
            "03EF97CD6A4919730DEA6F55579D86BAEEE:0\n"
        )
        mock_get.return_value.text = hashes

        for password, status_code, expected_result, exc in test_data:
            mock_get.return_value.status_code = status_code
            mock_get.side_effect = exc
            with self.subTest(pwd=password):
                result = is_password_compromised(password)
                self.assertIsInstance(result, tuple)
                self.assertLength(result, 2)
                self.assertEqual(result, expected_result)

    @tag('external')
    @skipUnless(settings.TEST_EXTERNAL_SERVICES, 'External services are tested only explicitly')
    def test_is_password_compromised_integration_contract(self):
        result = is_password_compromised("esperanto", full_list=True)
        self.assertLength(result, 3)
        all_hashes = result[2] + ('\n' if not result[2].endswith('\n') else '')
        self.assertRegex(all_hashes, r'^([A-F0-9]{35}:\d+\r?\n)+$')

    @override_settings(SECRET_KEY='JustASecret')
    def test_create_unique_url(self):
        test_data = [
            ("{aaa}", 'InthYWF9Ig'),
            ("/CCC/", 'Ii9DQ0MvIg'),
            ("", 'IiI'),
            ({'name': "A. User", 'profession': "Tester"}, 'eyJuYW1lIjoiQS4gVXNlciIsInByb2Zlc3Npb24iOiJUZXN0ZXIifQ'),
            ({}, 'e30'),
            # A large payload is gzipped and then base64-encoded.
            ("[Quite a long content over here]"*3, '.eJxTig4szSxJVUhUyMnPS1dIzs8rSc0rUcgvSy1SyEgtSo2lVF4JAN38I6k'),
        ]
        for payload, token_prefix in test_data:
            with self.subTest(payload=payload):
                result = create_unique_url(payload=payload, salt="bbbb")
                self.assertIs(type(result), tuple)
                self.assertLength(result, 2)
                self.assertStartsWith(result[0], '/ligilo/{}.'.format(token_prefix))
                self.assertStartsWith(result[1], '{}.'.format(token_prefix))
                self.assertEqual(result[1].count('.'), 3 if token_prefix.startswith('.') else 2)


@tag('utils')
class GeographicUtilityFunctionsTests(AdditionalAsserts, TestCase):
    @patch('geocoder.base.requests.Session.get')
    def test_geocode(self, mock_get):
        # An empty query is expected to return None.
        self.assertIsNone(geocode(""))

        mock_get.side_effect = HTTPConnectionError("Failed to establish a new connection. Max retries exceeded.")
        null_handler = logging.NullHandler()
        logging.getLogger('geocoder').addHandler(null_handler)
        result = geocode("Roterdamo", annotations=True)
        self.assertIs(type(result), OpenCageQuery)
        self.assertStartsWith(result.status, 'ERROR')
        self.assertLength(result, 0)
        self.assertIsNone(result.point)
        logging.getLogger('geocoder').removeHandler(null_handler)

        mock_get.return_value.json.return_value = {
            "rate": {"limit": 2500, "remaining": 2100, "reset": 1586908800},
            "licenses": [{"name": "see attribution guide", "url": "https://opencagedata.com/credits"}],
            "results": [{
                "annotations": {
                    "OSM": {
                        "url": "https://www.openstreetmap.org/?mlat=51.92290&mlon=4.46317#map=17/51.92290/4.46317"
                    },
                    "callingcode": 31,
                    "timezone": {"name": "Europe/Amsterdam", "short_name": "CEST"},
                },
                "bounds": {
                    "northeast": {"lat": 51.9942816, "lng": 4.6018083},
                    "southwest": {"lat": 51.8616672, "lng": 4.3793095},
                },
                "components": {
                    "ISO_3166-1_alpha-2": "NL",
                    "ISO_3166-1_alpha-3": "NLD",
                    "_category": "place",
                    "_type": "neighbourhood",
                    "city": "Roterdamo",
                    "continent": "Eŭropo",
                    "country": "Nederlando",
                    "country_code": "nl",
                    "political_union": "Eŭropa Unio",
                    "state": "Suda Holando",
                },
                "confidence": 5,
                "formatted": "Roterdamo, Suda Holando, Nederlando",
                "geometry": {"lat": 51.9228958, "lng": 4.4631727}
            }],
            "status": {"code": 200, "message": "OK"}, "total_results": 1
        }
        mock_get.return_value.status_code = 200
        mock_get.side_effect = None
        result = geocode("Roterdamo", annotations=True)
        self.assertIs(type(result), OpenCageQuery)
        self.assertEqual(result.status, 'OK')
        self.assertLength(result, 1)
        self.assertIs(type(result.current_result), OpenCageResult)
        self.assertGreater(len(result.current_result._annotations), 0)
        self.assertIsNotNone(result.point)
        self.assertIs(type(result.point), GeoPoint)

        mock_get.return_value.json.return_value = {
            "rate": {"limit": 2500, "remaining": 2100, "reset": 1586908800},
            "licenses": [{"name": "see attribution guide", "url": "https://opencagedata.com/credits"}],
            "results": [],
            "status": {"code": 200, "message": "OK"}, "total_results": 0
        }
        mock_get.return_value.status_code = 200
        mock_get.side_effect = None
        result = geocode("Roterdamo", 'PL', annotations=True)
        self.assertIs(type(result), OpenCageQuery)
        self.assertEqual(result.status, 'ERROR - No results found')
        self.assertLength(result, 0)
        self.assertIsNone(result.point)

    @patch('geocoder.base.requests.Session.get')
    def test_geocode_multiple(self, mock_get):
        # An empty query is expected to return None.
        self.assertIsNone(geocode("", multiple=True))

        mock_get.return_value.json.return_value = {
            "rate": {"limit": 2500, "remaining": 1900, "reset": 1586908800},
            "licenses": [{"name": "see attribution guide", "url": "https://opencagedata.com/credits"}],
            "results": [
                {
                    "components": {
                        "ISO_3166-1_alpha-2": "FR",
                        "ISO_3166-1_alpha-3": "FRA",
                        "_category": "place",
                        "_type": "city",
                        "city": "Parizo",
                        "continent": "Eŭropo",
                        "country": "Francio",
                        "country_code": "fr",
                        "county": "Parizo",
                        "political_union": "Eŭropa Unio",
                        "state": "Francilio"
                    },
                    "confidence": 6,
                    "formatted": "Parizo, Francio",
                    "geometry": {"lat": 48.8566969, "lng": 2.3514616},
                    "bounds": {
                        "northeast": {"lat": 48.902156, "lng": 2.4697602},
                        "southwest": {"lat": 48.8155755, "lng": 2.224122},
                    },
                }, {
                    "components": {
                        "ISO_3166-1_alpha-2": "US",
                        "ISO_3166-1_alpha-3": "USA",
                        "_category": "place",
                        "_type": "city",
                        "city": "Pariso",
                        "continent": "Norda Ameriko",
                        "country": "Usono",
                        "country_code": "us",
                        "county": "Lamar County",
                        "postcode": "75460",
                        "state": "Teksaso"
                    },
                    "confidence": 5,
                    "formatted": "Pariso, Teksaso, Usono",
                    "geometry": {"lat": 33.6617962, "lng": -95.555513},
                    "bounds": {
                        "northeast": {"lat": 33.7383866, "lng": -95.4354115},
                        "southwest": {"lat": 33.6206345, "lng": -95.6279396},
                    },
                }, {
                    "components": {
                        "ISO_3166-1_alpha-2": "US",
                        "ISO_3166-1_alpha-3": "USA",
                        "_category": "place",
                        "_type": "city",
                        "city": "Pariso",
                        "continent": "Norda Ameriko",
                        "country": "Usono",
                        "country_code": "us",
                        "county": "Bourbon County",
                        "state": "Kentukio"
                    },
                    "confidence": 7,
                    "formatted": "Pariso, Kentukio, Usono",
                    "geometry": {"lat": 38.2097987, "lng": -84.2529869},
                    "bounds": {
                        "northeast": {"lat": 38.238271, "lng": -84.232089},
                        "southwest": {"lat": 38.164922, "lng": -84.307326},
                    },
                }, {
                    "components": {
                        "ISO_3166-1_alpha-2": "CA",
                        "ISO_3166-1_alpha-3": "CAN",
                        "_category": "place",
                        "_type": "city",
                        "continent": "Norda Ameriko",
                        "country": "Kanado",
                        "country_code": "ca",
                        "county": "Brant County",
                        "postcode": "N3L 2M3",
                        "state": "Ontario",
                        "state_code": "ON",
                        "state_district": "Sudokcidenta Ontario",
                        "town": "Pariso"
                    },
                    "confidence": 7,
                    "formatted": "Pariso, ON N3L 2M3, Kanado",
                    "geometry": {"lat": 43.193234, "lng": -80.384281},
                    "bounds": {
                        "northeast": {"lat": 43.233234, "lng": -80.344281},
                        "southwest": {"lat": 43.153234, "lng": -80.424281},
                    },
                }, {
                    "components": {
                        "ISO_3166-1_alpha-2": "US",
                        "ISO_3166-1_alpha-3": "USA",
                        "_category": "place",
                        "_type": "village",
                        "city": "Hanover Township",
                        "continent": "Norda Ameriko",
                        "country": "Usono",
                        "country_code": "us",
                        "county": "Washington County",
                        "hamlet": "Paris",
                        "state": "Pensilvanio"
                    },
                    "confidence": 7,
                    "formatted": "Hanover Township, Pensilvanio, Usono",
                }
            ],
            "status": {"code": 200, "message": "OK"}, "total_results": 5
        }
        mock_get.return_value.status_code = 200
        result = geocode("Paris", multiple=True, private=True)
        self.assertIs(type(result), OpenCageQuery)
        self.assertEqual(result.status, 'OK')
        self.assertLength(result, 5)
        self.assertIs(type(result.current_result), OpenCageResult)
        self.assertIsNotNone(result.point)
        self.assertIs(type(result.point), GeoPoint)
        for i, r in enumerate(result):
            self.assertIs(type(r), OpenCageResult)
            self.assertLength(
                r.xy,
                2 if 'geometry' in mock_get.return_value.json.return_value['results'][i] else 0)
            self.assertEqual(r._annotations, {})
            self.assertEqual(
                r.country_code,
                mock_get.return_value.json.return_value['results'][i]['components']['country_code'])
            self.assertNotEqual(r._components, {})

    @patch('geocoder.base.requests.Session.get')
    def test_geocode_invalid_api_key_or_limit_reached(self, mock_get):
        test_data = (
            (
                401, HTTPError("401 Client Error: Unauthorized"),
                {},
                'ERROR - 401 Client Error: Unauthorized'
            ),
            (
                200, None,
                {"results": [], "status": {"code": 401, "message": "unknown API key"}, "total_results": 0},
                'unknown API key'
            ),
            (
                200, None,
                {"results": [], "status": {"code": 401, "message": "invalid API key"}, "total_results": 0},
                'invalid API key'
            ),
            (
                402, None,
                {"results": [], "status": {"code": 402, "message": "quota exceeded"}, "total_results": 0},
                'quota exceeded'
            ),
        )

        null_handler = logging.NullHandler()
        logging.getLogger('geocoder').addHandler(null_handler)
        for status_code, exc, json, expected_status in test_data:
            with self.subTest(status=expected_status):
                mock_get.return_value.json.return_value = json
                mock_get.return_value.status_code = status_code
                mock_get.return_value.raise_for_status.side_effect = exc
                result = geocode("Varsovio")
                self.assertIs(type(result), OpenCageQuery)
                self.assertEqual(result.status, expected_status)
                self.assertFalse(result.ok)
                self.assertLength(result, 0)
                self.assertIsNone(result.point)
        logging.getLogger('geocoder').removeHandler(null_handler)

    @tag('external')
    @skipUnless(settings.TEST_EXTERNAL_SERVICES, 'External services are tested only explicitly')
    def test_geocode_integration_contract(self):
        result = geocode("Harlem", 'US', multiple=True, annotations=True)
        self.assertEqual(result.status, 'OK')
        self.assertGreater(len(result), 10)
        for r in result:
            self.assertEqual(r.country_code.upper(), 'US')
            self.assertEqual(r.country, "Usono")
            self.assertNotEqual(r._annotations, {})
            self.assertEqual(r.callingcode, 1)
            self.assertEqual(r.raw['annotations']['currency']['iso_code'], 'USD')
            self.assertGreaterEqual(r.confidence, 7)
            self.assertLength(r.xy, 2)
            self.assertIn('northeast', r.bbox)
            self.assertIn('southwest', r.bbox)

    @patch('geocoder.base.requests.Session.get')
    def test_geocode_city(self, mock_get):
        mock_get.return_value.json.return_value = {
            "rate": {"limit": 2500, "remaining": 2399, "reset": 1586908800},
            "licenses": [{"name": "see attribution guide", "url": "https://opencagedata.com/credits"}],
            "results": [{
                "components": {
                    "ISO_3166-1_alpha-2": "US",
                    "ISO_3166-1_alpha-3": "USA",
                    "_category": "commerce",
                    "_type": "restaurant",
                    "city": "Providence",
                    "continent": "Norda Ameriko",
                    "country": "Usono",
                    "country_code": "us",
                    "county": "Providence County",
                    "neighbourhood": "Fox Point",
                    "postcode": "02903-2996",
                    "restaurant": "Tel Aviv",
                    "road": "Bridge Street",
                    "state": "Rod-Insulo"
                },
                "confidence": 9,
                "formatted": "Tel Aviv, Bridge Street, Providence, Rod-Insulo 02903-2996, Usono",
                "geometry": {"lat": 41.8174523, "lng": -71.4018689},
                "bounds": {
                    "northeast": {"lat": 41.8175371, "lng": -71.4017684},
                    "southwest": {"lat": 41.8173675, "lng": -71.4019694},
                },
            }],
            "status": {"code": 200, "message": "OK"}, "total_results": 1
        }
        mock_get.return_value.status_code = 200
        result = geocode_city("Tel aviv", state_province='Rhode Island', country='US')
        self.assertIsNone(result)

        mock_get.return_value.json.return_value = empty_result_set = {
            "rate": {"limit": 2500, "remaining": 2396, "reset": 1586908800},
            "licenses": [{"name": "see attribution guide", "url": "https://opencagedata.com/credits"}],
            "results": [],
            "status": {"code": 200, "message": "OK"}, "total_results": 0
        }
        mock_get.return_value.status_code = 200
        result = geocode_city("Varsovia", 'US')
        self.assertIsNone(result)

        mock_get.return_value.json.return_value = full_result_set = {
            "rate": {"limit": 2500, "remaining": 2393, "reset": 1586908800},
            "licenses": [{"name": "see attribution guide", "url": "https://opencagedata.com/credits"}],
            "results": [
                {
                    "components": {
                        "ISO_3166-1_alpha-2": "EC",
                        "ISO_3166-1_alpha-3": "ECU",
                        "_category": "place",
                        "_type": "village",
                        "continent": "South America",
                        "country": "Ekvadoro",
                        "country_code": "ec",
                        "county": "Montelibano",
                        "locality": "Varsovia",
                        "state": "Cordoba",
                        "state_code": "COR"
                    },
                    "confidence": 7,
                    "formatted": "Varsovia, Montelibano, Ekvadoro",
                    "geometry": {"lat": 7.965104, "lng": -75.3542833},
                }, {
                    "components": {
                        "ISO_3166-1_alpha-2": "EC",
                        "ISO_3166-1_alpha-3": "ECU",
                        "_category": "place",
                        "_type": "neighbourhood",
                        "continent": "South America",
                        "country": "Ekvadoro",
                        "country_code": "ec",
                        "county": "Calarca",
                        "neighbourhood": "Varsovia",
                        "postcode": "632001",
                        "state": "Quindio",
                        "state_code": "QUI",
                        "town": "Calarca"
                    },
                    "confidence": 9,
                    "formatted": "Varsovia, 632001 Calarca, QUI, Ekvadoro",
                    "geometry": {"lat": 4.5172617, "lng": -75.6444335},
                    "bounds": {
                        "northeast": {"lat": 4.5173117, "lng": -75.6443835},
                        "southwest": {"lat": 4.5172117, "lng": -75.6444835},
                    },
                }, {
                    "components": {
                        "ISO_3166-1_alpha-2": "EC",
                        "ISO_3166-1_alpha-3": "ECU",
                        "_category": "road",
                        "_type": "road",
                        "continent": "South America",
                        "country": "Ekvadoro",
                        "country_code": "ec",
                        "county": "Santa Rosa de Cabal",
                        "hamlet": "San Carlos",
                        "road": "Varsovia",
                        "road_type": "track",
                        "state": "Risaralda",
                        "state_code": "RIS"
                    },
                    "confidence": 9,
                    "formatted": "Varsovia, San Carlos, RIS, Ekvadoro",
                    "geometry": {"lat": 4.9212653, "lng": -75.6978718},
                    "bounds": {
                        "northeast": {"lat": 4.9254217, "lng": -75.6930418},
                        "southwest": {"lat": 4.9180269, "lng": -75.7019525},
                    },
                }, {
                    "components": {
                        "ISO_3166-1_alpha-2": "EC",
                        "ISO_3166-1_alpha-3": "ECU",
                        "_category": "place",
                        "_type": "village",
                        "city": "Monteria",
                        "continent": "South America",
                        "country": "Ekvadoro",
                        "country_code": "ec",
                        "county": "Monteria",
                        "locality": "Varsovia",
                        "state": "Cordoba",
                        "state_code": "COR"
                    },
                    "confidence": 7,
                    "formatted": "Monteria, Ekvadoro",
                    "geometry": {"lat": 8.3816971, "lng": -75.900398},
                    "bounds": {
                        "northeast": {"lat": 8.3916971, "lng": -75.890398},
                        "southwest": {"lat": 8.3716971, "lng": -75.910398},
                    },
                }, {
                    "components": {
                        "ISO_3166-1_alpha-2": "EC",
                        "ISO_3166-1_alpha-3": "ECU",
                        "_category": "commerce",
                        "_type": "bakery",
                        "bakery": "Varsovia",
                        "city": "Puente Aranda",
                        "continent": "South America",
                        "country": "Ekvadoro",
                        "country_code": "ec",
                        "county": "Bogota",
                        "neighbourhood": "Ciudad Montes",
                        "postcode": "111631",
                        "road": "Avenida Calle 8 Sur",
                        "state": "Distrito Capital",
                        "suburb": "Puente Aranda"
                    },
                    "confidence": 9,
                    "formatted": "Varsovia, Avenida Calle 8 Sur, 111631 Puente Aranda, Distrito Capital, Ekvadoro",
                    "geometry": {"lat": 4.604711, "lng": -74.1135704},
                    "bounds": {
                        "northeast": {"lat": 4.6047782, "lng": -74.1135039},
                        "southwest": {"lat": 4.6046437, "lng": -74.1136369},
                    },
                },
            ],
            "status": {"code": 200, "message": "OK"}, "total_results": 5
        }
        mock_get.return_value.status_code = 200
        # Originally the test was built with data for Colombia, but apparently
        # it is a federal state, so I had to switch the mock to Ecuador...
        result = geocode_city("Varsovia", state_province='COR', country='EC')
        self.assertIsNotNone(result)
        self.assertEqual(result.remaining_api_calls, 2393)
        self.assertEqual(result._components['_type'], 'village')
        self.assertEqual(result.confidence, 7)
        self.assertEqual(result.country_code.upper(), 'EC')
        self.assertEqual(result.city, "Monteria")
        self.assertEqual(result.village, "Varsovia")
        self.assertEqual(result.xy, [-75.900398, 8.3816971])

        mock_get.return_value.json.side_effect = [empty_result_set, full_result_set]
        mock_get.reset_mock()
        result = geocode_city("Varsovia", state_province='GUA', country='EC')
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual([result.state, result.city, result.village], ["Cordoba", "Monteria", "Varsovia"])

    @patch('geocoder.base.requests.Session.get')
    def test_emulate_geocode_country(self, mock_get):
        result = emulate_geocode_country('HK')
        mock_get.assert_not_called()
        self.assertIs(type(result), OpenCageResult)
        self.assertEqual(result.status, 'OK')
        self.assertEqual(result.country_code, 'HK')
        self.assertEqual(result.address, "Honkongo")
        self.assertEqual(result._annotations, {})
        self.assertNotEqual(result._components, {})
        self.assertLength(result.xy, 2)
        self.assertIsNotNone(result.point)
        self.assertIs(type(result.point), GeoPoint)

        result = emulate_geocode_country('QQ')
        mock_get.assert_not_called()
        self.assertIs(type(result), OpenCageResult)
        self.assertEqual(result.status, 'ERROR - No results found')
        self.assertFalse(result.ok)
        self.assertIsNone(result.point)

    @tag('subregions')
    def test_countries_with_mandatory_region(self):
        with self.assertRaises(UserWarning, msg="Result is not iterable."):
            try:
                iter(countries_with_mandatory_region())
            except TypeError:
                pass
            else:
                raise UserWarning
        with patch('hosting.countries.frozenset') as mock_set_object:
            countries = countries_with_mandatory_region()
            # Validate that the cache is only populated once.
            mock_set_object.assert_not_called()
            # Validate that the contents are 2-character country codes.
            self.assertTrue(
                all(isinstance(c, str) and len(c) == 2 and c.isalpha() for c in countries)
            )

    def test_bufferize_country_boundaries_unknown(self):
        self.assertIsNone(bufferize_country_boundaries('XYZ'))

    def test_bufferize_country_boundaries(self):
        country = random.choice(list(geodata.COUNTRIES_GEO))
        with self.subTest(country=country):
            res = bufferize_country_boundaries(country)
            self.assertIn('northeast', res['bbox'])
            self.assertLength(res['bbox']['northeast'], 2)
            self.assertIn('southwest', res['bbox'])
            self.assertLength(res['bbox']['southwest'], 2)
            self.assertEqual(res['center'], geodata.COUNTRIES_GEO[country]['center'])


@tag('utils')
class MassMailTests(AdditionalAsserts, TestCase):
    def test_empty_list(self):
        self.assertEqual(send_mass_html_mail(tuple()), 0)

    def test_mass_html_mail(self):
        test_data: list[tuple[str, str, str, str | None, list[str]]] = []
        test_subjects: list[tuple[str | None, str]] = []
        faker = Faker._get_faker()
        for i in range(random.randint(3, 7)):
            test_subjects.append((
                faker.optional_value(
                    'pystr_format', ratio=0.2 if i else 1.0,
                    string_format='{{word}}-{{random_int}}'),
                faker.sentence(),
            ))
            test_data.append((
                # subject line
                test_subjects[i][1]
                if not test_subjects[i][0]
                else f"[[{test_subjects[i][0]}]] \t {test_subjects[i][1]}",
                # content: plain text & html
                faker.word(), f"<hr /><strong>{faker.word()}</strong>",
                # author email & emails of recipients
                "test@ps" if i else None, [],
            ))
            for _ in range(random.randint(1, 3)):
                test_data[i][4].append(faker.company_email())

        result = send_mass_html_mail(test_data)
        self.assertEqual(result, len(test_data))
        self.assertLength(mail.outbox, len(test_data))
        for i in range(len(test_data)):
            self.assertEqual(mail.outbox[i].subject, test_subjects[i][1])
            if i == 0:
                self.assertEqual(mail.outbox[i].from_email, settings.DEFAULT_FROM_EMAIL)
            else:
                self.assertEqual(mail.outbox[i].from_email, "test@ps")
            self.assertEqual(mail.outbox[i].to, test_data[i][4])

        mail.outbox = []
        with override_settings(**settings.TEST_EMAIL_BACKENDS['dummy']):
            result = send_mass_html_mail(test_data)
        self.assertEqual(result, len(test_data))
        self.assertLength(mail.outbox, len(test_data))
        for i in range(len(test_data)):
            outbox_item = cast(AnymailMessage, mail.outbox[i])
            if test_subjects[i][0]:
                self.assertEqual(outbox_item.tags, [test_subjects[i][0]])
            else:
                self.assertEqual(outbox_item.tags, UNSET)
            self.assertTrue(outbox_item.anymail_test_params.get('is_batch_send'))
            self.assertFalse(outbox_item.anymail_test_params.get('track_opens'))

    def test_invalid_values(self):
        faker = Faker._get_faker()
        expected_subject = faker.sentence()
        test_data = [(
            # subject line
            "\n".join(expected_subject.split()),
            # content: plain text & html; author email
            "", "", "test@ps",
            # emails of recipients
            [f'{faker.email()}  ', f'  {faker.email()}', f'   {faker.email()} '],
        )]

        result = send_mass_html_mail(test_data)
        self.assertEqual(result, 1)
        self.assertLength(mail.outbox, 1)
        self.assertEqual(mail.outbox[0].subject, expected_subject.replace(" ", ""))
        self.assertEqual(mail.outbox[0].to, [email.strip() for email in test_data[0][-1]])
