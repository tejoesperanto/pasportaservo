import re
import string
from collections import namedtuple
from typing import TypedDict

from django.contrib.gis.geos import Point
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, tag

from djgeojson.templatetags.geojson_tags import geojsonfeature

from hosting.models import LocationConfidence
from maps import SRID

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
class FormatDMSFilterTests(TestCase):
    template = Template("{% load format_dms from geoformat %}{{ location|format_dms }}")

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({'location': "not a geo-point"}))
        with self.assertRaises(AttributeError):
            self.template.render(Context({'location': namedtuple('DummyObject', 'empty')(False)}))

    def test_empty_location(self):
        expected_result = "&uarr;&nbsp;&#xFF1F;&deg;, &rarr;&nbsp;&#xFF1F;&deg;"

        page = self.template.render(Context({'location': None}))
        self.assertHTMLEqual(page, expected_result)
        page = self.template.render(Context({'location': namedtuple('DummyPoint', 'empty')(True)}))
        self.assertHTMLEqual(page, expected_result)

    def test_given_location(self, template=None):
        expected_result = (
            f"{{arrlat}}&nbsp;{51}&deg;{54}&#8242;{49.617}&#8243;&thinsp;{{letlat}}, "
            f"{{arrlng}}&nbsp;{4}&deg;{27}&#8242;{52.014}&#8243;&thinsp;{{letlng}}"
        )

        tpl = template or self.template
        page = tpl.render(Context({'location': Point(coded_result.lng, coded_result.lat, srid=SRID)}))
        self.assertHTMLEqual(page, expected_result.format(arrlat="&uarr;", letlat="N", arrlng="&rarr;", letlng="E"))
        page = tpl.render(Context({'location': Point(coded_result.lng, -coded_result.lat, srid=SRID)}))
        self.assertHTMLEqual(page, expected_result.format(arrlat="&darr;", letlat="S", arrlng="&rarr;", letlng="E"))
        page = tpl.render(Context({'location': Point(-coded_result.lng, coded_result.lat, srid=SRID)}))
        self.assertHTMLEqual(page, expected_result.format(arrlat="&uarr;", letlat="N", arrlng="&larr;", letlng="W"))

    def test_confidence_high(self):
        self.test_given_location(Template(
            f"{{% load format_dms from geoformat %}}{{{{ location|format_dms:{LocationConfidence.ACCEPTABLE} }}}}"
        ))
        self.test_given_location(Template(
            f"{{% load format_dms from geoformat %}}{{{{ location|format_dms:{LocationConfidence.EXACT} }}}}"
        ))

    def test_confidence_low(self):
        expected_result = (
            f"{{arrlat}}&nbsp;{51}&deg;{54}&#8242;&thinsp;{{letlat}}, "
            f"{{arrlng}}&nbsp;{4}&deg;{27}&#8242;&thinsp;{{letlng}}"
        )
        page = Template("{% load format_dms from geoformat %}{{ location|format_dms:0 }}").render(
            Context({'location': Point(-coded_result.lng, -coded_result.lat, srid=SRID)}))
        self.assertHTMLEqual(page, expected_result.format(arrlat="&darr;", letlat="S", arrlng="&larr;", letlng="W"))


@tag('templatetags')
class IsLocationInCountryFilterTests(TestCase):
    MockPlace = namedtuple('MockPlace', 'country, location, location_confidence')
    template = Template("{% load is_location_in_country from geoformat %}{{ place|is_location_in_country }}")

    def setUp(self):
        self.loc = Point(coded_result.lng, coded_result.lat, srid=SRID)

    def test_unknown_location(self):
        page = self.template.render(Context({'place': self.MockPlace('NL', None, 0)}))
        self.assertEqual(page, str(False))
        page = self.template.render(Context({'place': self.MockPlace('NL', Point([]), 0)}))
        self.assertEqual(page, str(False))

    def test_imprecise_location(self):
        page = self.template.render(Context({
            'place': self.MockPlace('NL', self.loc, LocationConfidence.UNDETERMINED),
        }))
        self.assertEqual(page, str(False))

    def test_location_in_country(self):
        for conf in (LocationConfidence.ACCEPTABLE, LocationConfidence.EXACT, LocationConfidence.CONFIRMED):
            with self.subTest(confidence=conf):
                page = self.template.render(Context({
                    'place': self.MockPlace('NL', self.loc, conf),
                }))
                self.assertEqual(page, str(True))

    def test_location_outside_country(self):
        for conf in (LocationConfidence.ACCEPTABLE, LocationConfidence.EXACT):
            with self.subTest(confidence=conf):
                page = self.template.render(Context({
                    'place': self.MockPlace('CH', self.loc, conf),
                }))
                self.assertEqual(page, str(False))
            page = self.template.render(Context({
                'place': self.MockPlace('PL', self.loc, LocationConfidence.CONFIRMED),
            }))
            self.assertEqual(page, str(True))


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


@tag('templatetags')
class GeoJSONFeatureStylingFilterTests(TestCase):
    template = Template(
        "{% load geojsonfeature_styling from geoformat %}"
        "{{ geoobject|geojsonfeature_styling:style }}"
    )
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        class TestParams(TypedDict):
            tag: str
            obj: str
            res: string.Template

        cls.test_dataset: list[TestParams] = [
            {
                'tag': "null",
                'obj': "null",
                'res': string.Template("null"),
            }, {
                'tag': "raw_object",
                'obj': Point(10, 20, srid=SRID).geojson,
                'res': string.Template("""
                {
                    "type": "Point",
                    "coordinates": [10.0, 20.0]
                }
                """),
            }, {
                'tag': "feature",
                'obj': geojsonfeature(Point(20, 30, srid=SRID)),
                'res': string.Template("""
                {
                    "type": "Feature",
                    "properties": {$STYLE1},
                    "geometry": {"type": "Point", "coordinates": [20.0, 30.0]}
                }
                """),
            }, {
                'tag': "featureset_one",
                'obj': geojsonfeature([{'geom': Point(30, 40, srid=SRID)}]),
                'res': string.Template("""
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {$STYLE1},
                            "geometry": {"type": "Point", "coordinates": [30.0, 40.0]}
                        }
                    ],
                    "crs": {
                        "type": "link",
                        "properties": {
                            "href": "http://spatialreference.org/ref/epsg/4326/",
                            "type":"proj4"
                        }
                    }
                }
                """),
            }, {
                'tag': "featureset_many",
                'obj': geojsonfeature([
                    {'geom': Point(41, 51, srid=SRID)},
                    {'geom': Point(52, 62, srid=SRID)},
                    {'geom': Point(63, 73, srid=SRID)},
                ]),
                'res': string.Template("""
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {$STYLE1},
                            "geometry": {"type": "Point", "coordinates": [41.0, 51.0]}
                        }, {
                            "type": "Feature",
                            "properties": {$STYLE2},
                            "geometry": {"type": "Point", "coordinates": [52.0, 62.0]}
                        }, {
                            "type": "Feature",
                            "properties": {$STYLE3},
                            "geometry": {"type": "Point", "coordinates": [63.0,73.0]}
                        }
                    ]
                    $CRS_START
                    ,
                    "crs": {
                        "type": "link",
                        "properties": {
                            "href": "http://spatialreference.org/ref/epsg/4326/",
                            "type": "proj4"
                        }
                    }
                    $CRS_END
                }
                """),
            }
        ]

    def test_invalid_type(self):
        # The filter is expected to be applied to a GeoJSON object,
        # already serialized to a string.
        with self.assertRaises(TypeError) as cm:
            self.template.render(Context({'geoobject': None, 'style': None}))
        self.assertEqual(
            "the JSON object must be str, bytes or bytearray, not NoneType",
            str(cm.exception)
        )

        with self.assertRaises(TypeError) as cm:
            self.template.render(Context({'geoobject': Point(), 'style': None}))
        self.assertEqual(
            "the JSON object must be str, bytes or bytearray, not Point",
            str(cm.exception)
        )

    def test_missing_style_param(self):
        # The style parameter is expected to be non-optional.
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                "{% load geojsonfeature_styling from geoformat %}"
                "{{ geoobject|geojsonfeature_styling }}"
            )
        self.assertEqual(
            "geojsonfeature_styling requires 2 arguments, 1 provided",
            str(cm.exception)
        )

        # When the style parameter is given but is None, the geojson string
        # is expected to be returned as-is, without modification and without
        # an error.
        for test_data in self.test_dataset:
            with self.subTest(tag=test_data['tag']):
                page = self.template.render(
                    Context({
                        'geoobject': test_data['obj'], 'style': None,
                    })
                )
                self.assertHTMLEqual(
                    page.replace(" ", ""),
                    test_data['res'].substitute(
                                        STYLE1="", STYLE2="", STYLE3="",
                                        CRS_START="", CRS_END="")
                                    .replace("\n", " ").replace(" ", ""),
                )

    def test_single_style(self):
        # When a single style is provided as the filter parameter's value,
        # all features in the geojson are expected to use this style.
        style = {'fill': "#012", 'title': "GeoObject"}
        style_string = """
            "fill": "#012", "title": "GeoObject"
        """
        for test_data in self.test_dataset:
            with self.subTest(tag=test_data['tag']):
                page = self.template.render(
                    Context({
                        'geoobject': test_data['obj'], 'style': style,
                    })
                )
                self.assertHTMLEqual(
                    page.replace(" ", ""),
                    test_data['res'].substitute(
                                        STYLE1=style_string,
                                        STYLE2=style_string,
                                        STYLE3=style_string,
                                        CRS_START="", CRS_END="")
                                    .replace("\n", " ").replace(" ", ""),
                )

    def test_multiple_styles(self):
        test_data = next(filter(
            lambda data: data['tag'] == "featureset_many",
            self.test_dataset))

        # When a list of styles is provided as the filter parameter's value,
        # and it contains less styles than features in the geojson, only the
        # first features are expected to use these styles – and the rest are
        # expected to remain unstyled.
        style = [
            {'marker-symbol': "bus", 'marker__size': "small"},
            {'stroke__width': 8},
        ]
        style_strings = [
            """ "marker-symbol": "bus", "marker-size": "small" """,
            """ "stroke-width": 8 """,
        ]
        with self.subTest(tag=test_data['tag'], styles=2):
            page = self.template.render(
                Context({
                    'geoobject': test_data['obj'], 'style': style,
                })
            )
            self.assertHTMLEqual(
                page.replace(" ", ""),
                test_data['res'].substitute(
                                    STYLE1=style_strings[0],
                                    STYLE2=style_strings[1],
                                    STYLE3="",
                                    CRS_START="", CRS_END="")
                                .replace("\n", " ").replace(" ", "")
            )

        # When a list of styles is provided as the filter parameter's value,
        # and it contains more styles than features in the geojson, all of
        # the features are expected to be styled accordingly, and any of the
        # remaining styles are expected to be discarded.
        style = [
            {'fill': "#123"},
            {'stroke': "#565656"},
            {'title': "GeoObject"},
            {'description': "Invisible"},
        ]
        style_strings = [
            """ "fill": "#123" """,
            """ "stroke": "#565656" """,
            """ "title": "GeoObject" """,
        ]
        with self.subTest(tag=test_data['tag'], styles=4):
            page = self.template.render(
                Context({
                    'geoobject': test_data['obj'], 'style': style,
                })
            )
            self.assertHTMLEqual(
                page.replace(" ", ""),
                test_data['res'].substitute(
                                    STYLE1=style_strings[0],
                                    STYLE2=style_strings[1],
                                    STYLE3=style_strings[2],
                                    CRS_START="", CRS_END="")
                                .replace("\n", " ").replace(" ", "")
            )

    def test_crs_removal(self):
        # When any of the styles provided as the filter parameter's value
        # contains a `crs` flag set to None or False, the 'crs' component
        # is expected to be removed from the geojson's feature collection.
        test_dataset = filter(
            lambda data: data['tag'] in ("feature", "featureset_many"),
            self.test_dataset)
        style = [
            {},
            {'crs': None},
            {'crs': True},
        ]
        for test_data in test_dataset:
            with self.subTest(tag=test_data['tag']):
                page = self.template.render(
                    Context({
                        'geoobject': test_data['obj'], 'style': style,
                    })
                )
                result_template = string.Template(
                    re.sub(
                        r'\$CRS_START.+\$CRS_END',
                        '',
                        test_data['res'].template,
                        flags=re.DOTALL,
                    )
                )
                self.assertHTMLEqual(
                    page.replace(" ", ""),
                    result_template.substitute(
                                        STYLE1="", STYLE2="", STYLE3="")
                                   .replace("\n", " ").replace(" ", ""),
                )
