from django.test import TestCase, override_settings, tag

from ..factories import CountryRegionFactory


@tag('models')
class CountryRegionModelTests(TestCase):
    def test_field_max_lengths(self):
        region = CountryRegionFactory.build()
        self.assertEquals(region._meta.get_field('iso_code').max_length, 4)
        self.assertEquals(region._meta.get_field('latin_code').max_length, 70)
        self.assertEquals(region._meta.get_field('latin_name').max_length, 70)
        self.assertEquals(region._meta.get_field('local_code').max_length, 70)
        self.assertEquals(region._meta.get_field('local_name').max_length, 70)
        self.assertEquals(region._meta.get_field('esperanto_name').max_length, 70)

    @override_settings(LANGUAGE_CODE='en')
    def test_str(self):
        region = CountryRegionFactory.build(short_code=False)
        self.assertEquals(
            str(region),
            f"{region.country.code}: {region.latin_code}"
        )
        region = CountryRegionFactory.build(short_code=True)
        self.assertEquals(
            str(region),
            f"{region.country.code}: {region.latin_name} ({region.latin_code})"
        )
