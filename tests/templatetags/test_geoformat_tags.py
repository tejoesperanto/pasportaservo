from collections import namedtuple

from django.template import Context, Template
from django.test import TestCase, tag

MockResult = namedtuple('MockResult', 'address, country, country_code, city, lat, lng, latlng')

coded_result = MockResult(
    address='Nieuwe Binnenweg 176, 3015 BJ Roterdamo, Reĝlando Nederlando',
    city='Roterdamo', country='Reĝlando Nederlando', country_code='nl',
    lat=51.9137824, lng=4.4644483, latlng=(51.9137824, 4.4644483))


@tag('templatetags')
class FormatResultFilterTests(TestCase):
    template = Template("{% load format_geo_result from geoformat %}{{ result|format_geo_result }}")
    basic_result = coded_result

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({'result': "not a geocoding result"}))

    def test_no_country_name(self):
        geocoding_result = self.basic_result._replace(country=None)
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, geocoding_result.address)

        geocoding_result = MockResult(
            address=None, city='Roterdamo', country=None, country_code=None,
            lat=self.basic_result.lat, lng=self.basic_result.lng, latlng=[])
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "")

    def test_no_country_code(self):
        geocoding_result = self.basic_result._replace(country_code=None)
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, geocoding_result.address)

        geocoding_result = MockResult(
            address=None, city='Roterdamo', country='Nederlando', country_code=None,
            lat=self.basic_result.lat, lng=self.basic_result.lng, latlng=[])
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "None")

    def test_invalid_country_code(self):
        geocoding_result = self.basic_result._replace(country_code='abc')
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, geocoding_result.address)

        geocoding_result = self.basic_result._replace(address=None, country_code='abc')
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "None")

    def test_valid_object(self):
        page = self.template.render(Context({'result': self.basic_result}))
        self.assertEqual(page, "Nieuwe Binnenweg 176, 3015 BJ Roterdamo, Nederlando")

        geocoding_result = MockResult(
            address='str. Ŝĉerbakovskaja 32/7-292, Moskvo, Rusuja Federacio, 105318',
            city='Moskvo', country='Rusuja Federacio', country_code='ru',
            lat=55.4656, lng=51.2614, latlng=(55.4656, 51.2614))
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "str. Ŝĉerbakovskaja 32/7-292, Moskvo, 105318, Rusio")


@tag('templatetags')
class ResultCountryFilterTests(TestCase):
    template = Template("{% load geo_result_country from geoformat %}{{ result|geo_result_country }}")
    basic_result = coded_result

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({'result': "not a geocoding result"}))

    def test_no_country_code(self):
        geocoding_result = self.basic_result._replace(country_code=None)
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "Reĝlando Nederlando")

        geocoding_result = self.basic_result._replace(country_code=None, country=None)
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "None")

    def test_invalid_country_code(self):
        geocoding_result = self.basic_result._replace(country_code='abc')
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "Reĝlando Nederlando")

        geocoding_result = self.basic_result._replace(country_code='abc', country=None)
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "None")

    def test_valid_object(self):
        page = self.template.render(Context({'result': self.basic_result}))
        self.assertEqual(page, "Nederlando")

        geocoding_result = MockResult(None, 'Rusuja Federacio', 'ru', None, 0, 0, [])
        page = self.template.render(Context({'result': geocoding_result}))
        self.assertEqual(page, "Rusio")


@tag('templatetags')
class GeoURLHashFilterTests(TestCase):
    template = Template("{% load geo_url_hash from geoformat %}{{ result|geo_url_hash }}")
    basic_result = coded_result

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({'result': "not a geocoding result"}))

    def test_missing_coordinates(self):
        for empty_values in ({'lat': None, 'lng': None, 'latlng': None},
                             {'lat': '', 'lng': '', 'latlng': []}):
            geocoding_result = self.basic_result._replace(**empty_values)
            page = self.template.render(Context({'result': geocoding_result}))
            self.assertEqual(page, "")

    def test_valid_object(self):
        # Continent level hash is expected to be at zoom 4.
        page = self.template.render(Context({'result': self.basic_result._replace(city=None, country=None)}))
        self.assertEqual(page, "#4/51.9137824/4.4644483")
        # Country level hash is expected to be at zoom 6.
        page = self.template.render(Context({'result': self.basic_result._replace(city=None)}))
        self.assertEqual(page, "#6/51.9137824/4.4644483")
        # City level hash is expected to be at zoom 8.
        page = self.template.render(Context({'result': self.basic_result}))
        self.assertEqual(page, "#8/51.9137824/4.4644483")
