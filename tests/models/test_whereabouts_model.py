from django_countries.fields import Country
from django_webtest import WebTest
from factory import Faker

from ..factories import WhereaboutsFactory


class WhereaboutsModelTests(WebTest):
    def test_field_max_lengths(self):
        loc = WhereaboutsFactory.build()
        self.assertEquals(loc._meta.get_field('type').max_length, 1)
        self.assertEquals(loc._meta.get_field('name').max_length, 255)
        self.assertEquals(loc._meta.get_field('state').max_length, 70)
        self.assertEquals(loc._meta.get_field('name').max_length, 255)

    def test_str(self):
        loc = WhereaboutsFactory.build(name="Córdoba", state="", country=Country('AR'))
        self.assertEquals(str(loc), "Location of Córdoba (Argentino)")
        loc = WhereaboutsFactory.build(name="Córdoba", state="Córdoba", country=Country('AR'))
        self.assertEquals(str(loc), "Location of Córdoba (Córdoba, Argentino)")
        loc = WhereaboutsFactory.build(
            name=Faker('city', locale='el_GR'), state="", country=Country('GR'))
        self.assertEquals(str(loc), "Location of {} ({})".format(loc.name, loc.country.name))
        loc = WhereaboutsFactory.build(
            name=Faker('city', locale='el_GR'), state=Faker('region', locale='el_GR'), country=Country('GR'))
        self.assertEquals(str(loc), "Location of {} ({}, {})".format(loc.name, loc.state, loc.country.name))
