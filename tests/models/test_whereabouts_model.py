from django.test import override_settings, tag

from django_countries.fields import Country
from django_webtest import WebTest
from factory import Faker

from ..assertions import AdditionalAsserts
from ..factories import WhereaboutsFactory


@tag('models')
class WhereaboutsModelTests(AdditionalAsserts, WebTest):
    def test_field_max_lengths(self):
        loc = WhereaboutsFactory.build()
        self.assertEqual(loc._meta.get_field('type').max_length, 1)
        self.assertEqual(loc._meta.get_field('name').max_length, 255)
        self.assertEqual(loc._meta.get_field('state').max_length, 70)
        self.assertEqual(loc._meta.get_field('name').max_length, 255)

    def test_str(self):
        loc = WhereaboutsFactory.build(name="Córdoba", state="", country=Country('AR'))
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(str(loc), "Location of Córdoba (Argentina)")
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(str(loc), "Lokigo de Córdoba (Argentino)")

        loc = WhereaboutsFactory.build(name="Córdoba", state="Córdoba", country=Country('AR'))
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(str(loc), "Location of Córdoba (Córdoba, Argentina)")
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(str(loc), "Lokigo de Córdoba (Córdoba, Argentino)")

        loc = WhereaboutsFactory.build(
            name=Faker('city', locale='el_GR'), state="", country=Country('GR'))
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(str(loc), "Location of {} ({})".format(loc.name, loc.country.name))
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(str(loc), "Lokigo de {} ({})".format(loc.name, loc.country.name))

        loc = WhereaboutsFactory.build(
            name=Faker('city', locale='el_GR'), state=Faker('region', locale='el_GR'), country=Country('GR'))
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(str(loc), "Location of {} ({}, {})".format(loc.name, loc.state, loc.country.name))
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(str(loc), "Lokigo de {} ({}, {})".format(loc.name, loc.state, loc.country.name))

    def test_repr(self):
        loc = WhereaboutsFactory.build()
        self.assertSurrounding(repr(loc), "<Whereabouts:", f"SW{loc.bbox.coords[0]} NE{loc.bbox.coords[1]}>")
