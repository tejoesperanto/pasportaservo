from collections import namedtuple

from django.contrib.gis.geos import Point
from django.template import Context, Template
from django.test import TestCase, tag

from hosting.models import LocationConfidence
from maps import SRID

MockResult = namedtuple(
    "MockResult", "address, country, country_code, city, lat, lng, latlng"
)

coded_result = MockResult(
    address="Nieuwe Binnenweg 176, 3015 BJ Roterdamo, Reĝlando Nederlando",
    city="Roterdamo",
    country="Reĝlando Nederlando",
    country_code="nl",
    lat=51.9137824,
    lng=4.4644483,
    latlng=(51.9137824, 4.4644483),
)


@tag("templatetags")
class FormatResultFilterTests(TestCase):
    template = Template(
        "{% load format_geo_result from geoformat %}{{ result|format_geo_result }}"
    )
    basic_result = coded_result

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({"result": "not a geocoding result"}))

    def test_no_country_name(self):
        geocoding_result = self.basic_result._replace(country=None)
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, geocoding_result.address)

        geocoding_result = MockResult(
            address=None,
            city="Roterdamo",
            country=None,
            country_code=None,
            lat=self.basic_result.lat,
            lng=self.basic_result.lng,
            latlng=[],
        )
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "")

    def test_no_country_code(self):
        geocoding_result = self.basic_result._replace(country_code=None)
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, geocoding_result.address)

        geocoding_result = MockResult(
            address=None,
            city="Roterdamo",
            country="Nederlando",
            country_code=None,
            lat=self.basic_result.lat,
            lng=self.basic_result.lng,
            latlng=[],
        )
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "None")

    def test_invalid_country_code(self):
        geocoding_result = self.basic_result._replace(country_code="abc")
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, geocoding_result.address)

        geocoding_result = self.basic_result._replace(address=None, country_code="abc")
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "None")

    def test_valid_object(self):
        page = self.template.render(Context({"result": self.basic_result}))
        self.assertEqual(page, "Nieuwe Binnenweg 176, 3015 BJ Roterdamo, Nederlando")

        geocoding_result = MockResult(
            address="str. Ŝĉerbakovskaja 32/7-292, Moskvo, Rusuja Federacio, 105318",
            city="Moskvo",
            country="Rusuja Federacio",
            country_code="ru",
            lat=55.4656,
            lng=51.2614,
            latlng=(55.4656, 51.2614),
        )
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "str. Ŝĉerbakovskaja 32/7-292, Moskvo, 105318, Rusio")


@tag("templatetags")
class ResultCountryFilterTests(TestCase):
    template = Template(
        "{% load geo_result_country from geoformat %}{{ result|geo_result_country }}"
    )
    basic_result = coded_result

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({"result": "not a geocoding result"}))

    def test_no_country_code(self):
        geocoding_result = self.basic_result._replace(country_code=None)
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "Reĝlando Nederlando")

        geocoding_result = self.basic_result._replace(country_code=None, country=None)
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "None")

    def test_invalid_country_code(self):
        geocoding_result = self.basic_result._replace(country_code="abc")
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "Reĝlando Nederlando")

        geocoding_result = self.basic_result._replace(country_code="abc", country=None)
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "None")

    def test_valid_object(self):
        page = self.template.render(Context({"result": self.basic_result}))
        self.assertEqual(page, "Nederlando")

        geocoding_result = MockResult(None, "Rusuja Federacio", "ru", None, 0, 0, [])
        page = self.template.render(Context({"result": geocoding_result}))
        self.assertEqual(page, "Rusio")


@tag("templatetags")
class FormatDMSFilterTests(TestCase):
    template = Template("{% load format_dms from geoformat %}{{ location|format_dms }}")

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({"location": "not a geo-point"}))
        with self.assertRaises(AttributeError):
            self.template.render(
                Context({"location": namedtuple("DummyObject", "empty")(False)})
            )

    def test_empty_location(self):
        expected_result = "&8593;&nbsp;&#xFF1F;&deg;, &8594;&nbsp;&#xFF1F;&deg;"
        # TODO: In Django 3 "&uarr; &#xff1f;&deg;, &larr; &#xff1f;&deg;"

        page = self.template.render(Context({"location": None}))
        self.assertHTMLEqual(page, expected_result)
        page = self.template.render(
            Context({"location": namedtuple("DummyPoint", "empty")(True)})
        )
        self.assertHTMLEqual(page, expected_result)

    def test_given_location(self, template=None):
        expected_result = (
            f"{{arrlat}}&nbsp;{51}&deg;{54}&#8242;{49.617}&#8243;&thinsp;{{letlat}}, "
            f"{{arrlng}}&nbsp;{4}&deg;{27}&#8242;{52.014}&#8243;&thinsp;{{letlng}}"
        )

        tpl = template or self.template
        page = tpl.render(
            Context({"location": Point(coded_result.lng, coded_result.lat, srid=SRID)})
        )
        self.assertHTMLEqual(
            page,
            expected_result.format(
                arrlat="&8593;", letlat="N", arrlng="&8594;", letlng="E"
            ),
        )
        page = tpl.render(
            Context({"location": Point(coded_result.lng, -coded_result.lat, srid=SRID)})
        )
        self.assertHTMLEqual(
            page,
            expected_result.format(
                arrlat="&8595;", letlat="S", arrlng="&8594;", letlng="E"
            ),
        )
        page = tpl.render(
            Context({"location": Point(-coded_result.lng, coded_result.lat, srid=SRID)})
        )
        self.assertHTMLEqual(
            page,
            expected_result.format(
                arrlat="&8593;", letlat="N", arrlng="&8592;", letlng="W"
            ),
        )

    def test_confidence_high(self):
        self.test_given_location(
            Template(
                f"{{% load format_dms from geoformat %}}{{{{ location|format_dms:{LocationConfidence.ACCEPTABLE} }}}}"
            )
        )
        self.test_given_location(
            Template(
                f"{{% load format_dms from geoformat %}}{{{{ location|format_dms:{LocationConfidence.EXACT} }}}}"
            )
        )

    def test_confidence_low(self):
        expected_result = (
            f"{{arrlat}}&nbsp;{51}&deg;{54}&#8242;&thinsp;{{letlat}}, "
            f"{{arrlng}}&nbsp;{4}&deg;{27}&#8242;&thinsp;{{letlng}}"
        )
        page = Template(
            "{% load format_dms from geoformat %}{{ location|format_dms:0 }}"
        ).render(
            Context(
                {"location": Point(-coded_result.lng, -coded_result.lat, srid=SRID)}
            )
        )
        self.assertHTMLEqual(
            page,
            expected_result.format(
                arrlat="&8595;", letlat="S", arrlng="&8592;", letlng="W"
            ),
        )


@tag("templatetags")
class IsLocationInCountryFilterTests(TestCase):
    MockPlace = namedtuple("MockPlace", "country, location, location_confidence")
    template = Template(
        "{% load is_location_in_country from geoformat %}{{ place|is_location_in_country }}"
    )

    def setUp(self):
        self.loc = Point(coded_result.lng, coded_result.lat, srid=SRID)

    def test_unknown_location(self):
        page = self.template.render(Context({"place": self.MockPlace("NL", None, 0)}))
        self.assertEqual(page, str(False))
        page = self.template.render(
            Context({"place": self.MockPlace("NL", Point([]), 0)})
        )
        self.assertEqual(page, str(False))

    def test_imprecise_location(self):
        page = self.template.render(
            Context(
                {
                    "place": self.MockPlace(
                        "NL", self.loc, LocationConfidence.UNDETERMINED
                    ),
                }
            )
        )
        self.assertEqual(page, str(False))

    def test_location_in_country(self):
        for conf in (
            LocationConfidence.ACCEPTABLE,
            LocationConfidence.EXACT,
            LocationConfidence.CONFIRMED,
        ):
            with self.subTest(confidence=conf):
                page = self.template.render(
                    Context(
                        {
                            "place": self.MockPlace("NL", self.loc, conf),
                        }
                    )
                )
                self.assertEqual(page, str(True))

    def test_location_outside_country(self):
        for conf in (LocationConfidence.ACCEPTABLE, LocationConfidence.EXACT):
            with self.subTest(confidence=conf):
                page = self.template.render(
                    Context(
                        {
                            "place": self.MockPlace("CH", self.loc, conf),
                        }
                    )
                )
                self.assertEqual(page, str(False))
            page = self.template.render(
                Context(
                    {
                        "place": self.MockPlace(
                            "PL", self.loc, LocationConfidence.CONFIRMED
                        ),
                    }
                )
            )
            self.assertEqual(page, str(True))


@tag("templatetags")
class GeoURLHashFilterTests(TestCase):
    template = Template(
        "{% load geo_url_hash from geoformat %}{{ result|geo_url_hash }}"
    )
    basic_result = coded_result

    def test_invalid_object(self):
        with self.assertRaises(AttributeError):
            self.template.render(Context({"result": "not a geocoding result"}))

    def test_missing_coordinates(self):
        for empty_values in (
            {"lat": None, "lng": None, "latlng": None},
            {"lat": "", "lng": "", "latlng": []},
        ):
            geocoding_result = self.basic_result._replace(**empty_values)
            page = self.template.render(Context({"result": geocoding_result}))
            self.assertEqual(page, "")

    def test_valid_object(self):
        # Continent level hash is expected to be at zoom 4.
        page = self.template.render(
            Context({"result": self.basic_result._replace(city=None, country=None)})
        )
        self.assertEqual(page, "#4/51.9137824/4.4644483")
        # Country level hash is expected to be at zoom 6.
        page = self.template.render(
            Context({"result": self.basic_result._replace(city=None)})
        )
        self.assertEqual(page, "#6/51.9137824/4.4644483")
        # City level hash is expected to be at zoom 8.
        page = self.template.render(Context({"result": self.basic_result}))
        self.assertEqual(page, "#8/51.9137824/4.4644483")
