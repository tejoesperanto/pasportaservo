from itertools import product
from unittest.mock import PropertyMock, patch

from django.test import TestCase, override_settings, tag

from ..factories import CountryRegionFactory


@tag('models', 'subregions')
class CountryRegionModelTests(TestCase):
    def test_field_max_lengths(self):
        region = CountryRegionFactory.build()
        self.assertEqual(region._meta.get_field('iso_code').max_length, 4)
        self.assertEqual(region._meta.get_field('latin_code').max_length, 70)
        self.assertEqual(region._meta.get_field('latin_name').max_length, 70)
        self.assertEqual(region._meta.get_field('local_code').max_length, 70)
        self.assertEqual(region._meta.get_field('local_name').max_length, 70)
        self.assertEqual(region._meta.get_field('esperanto_name').max_length, 70)

    def test_translated_name(self):
        # For region with no Esperanto name, value is expected to be empty string.
        region = CountryRegionFactory.build(esperanto_name="")
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(region.translated_name, "")
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(region.translated_name, "")

        # For region with an Esperanto name, value is expected to be that name when
        # locale is Esperanto and an empty string for any other locale.
        region = CountryRegionFactory.build()
        with override_settings(LANGUAGE_CODE='eo'):
            self.assertEqual(region.translated_name, region.esperanto_name)
        with override_settings(LANGUAGE_CODE='en'):
            self.assertEqual(region.translated_name, "")

    def test_translated_or_latin_name(self):
        region_with_eo_and_code = CountryRegionFactory.build(short_code=True)
        region_with_eo_and_name = CountryRegionFactory.build(short_code=False)
        region_without_eo_with_code = CountryRegionFactory.build(short_code=True, esperanto_name="")
        region_without_eo_with_name = CountryRegionFactory.build(short_code=False, esperanto_name="")

        with override_settings(LANGUAGE_CODE='eo'):
            # For region with an Esperanto name, value is expected to be that name for Esperanto locale.
            self.assertEqual(
                region_with_eo_and_code.translated_or_latin_name, region_with_eo_and_code.esperanto_name)
            self.assertEqual(
                region_with_eo_and_name.translated_or_latin_name, region_with_eo_and_name.esperanto_name)
            # For region with no Esperanto name,
            # value is expected to be the latin name or code for Esperanto locale.
            self.assertEqual(
                region_without_eo_with_code.translated_or_latin_name, region_without_eo_with_code.latin_name)
            self.assertEqual(
                region_without_eo_with_name.translated_or_latin_name, region_without_eo_with_name.latin_code)
        with override_settings(LANGUAGE_CODE='en'):
            # For region with an Esperanto name,
            # value is expected to be the latin name or code for non-Esperanto locale.
            self.assertEqual(
                region_with_eo_and_code.translated_or_latin_name, region_with_eo_and_code.latin_name)
            self.assertEqual(
                region_with_eo_and_name.translated_or_latin_name, region_with_eo_and_name.latin_code)
            # For region with no Esperanto name,
            # value is expected to be the latin name or code for non-Esperanto locale.
            self.assertEqual(
                region_without_eo_with_code.translated_or_latin_name, region_without_eo_with_code.latin_name)
            self.assertEqual(
                region_without_eo_with_name.translated_or_latin_name, region_without_eo_with_name.latin_code)

    def test_display_value(self):
        test_data = [
            (
                # For region with latin code and latin name, value is expected to be the latin name.
                dict(latin_code="ABC", latin_name="Appa Balwant Chowk"),
                "Appa Balwant Chowk"
            ), (
                # For region with only latin code and no latin name, value is expected to be the latin code.
                dict(latin_code="Shaniwar Peth", latin_name=""),
                "Shaniwar Peth"
            ), (
                # For region with latin code equal to the local code, value is expected to be only one of them.
                dict(latin_code="Aundh", latin_name="", local_code="Aundh"),
                "Aundh"
            ), (
                # For region with local code similar to the latin code, value is expected to be the local code.
                dict(latin_code="Balewadi", latin_name="", local_code="Báłěwàďı"),
                "Báłěwàďı"
            ), (
                # For region with local code, value is expected to be latin code with the local code.
                dict(latin_code="Baner", latin_name="", local_code="बाणेर"),
                "Baner (बाणेर)"
            ), (
                # For region with both local code and name, value is expected to be latin code with the local name.
                dict(latin_code="Baner", latin_name="", local_code="BNR", local_name="बाणेर"),
                "Baner (बाणेर)"
            ), (
                # For region with latin code equal to local code with addition of prefix or suffix,
                # value is expected to be only the local code.
                dict(latin_code="Neighbourhood of Bavdhan", latin_name="", local_code="Bavdhan"),
                "Bavdhan"
            ), (
                # For region with latin code equal to local code minus a prefix or a suffix,
                # value is expected to be only the local code.
                dict(latin_code="Bavdhan", latin_name="", local_code="Bavdhan Locality"),
                "Bavdhan Locality"
            ), (
                # For region with latin code similar to local code and with addition of prefix or suffix,
                # value is expected to be both latin code with the local code.
                dict(latin_code="Neighbourhood of Bavdhan", latin_name="", local_code="Bāvdhān"),
                "Neighbourhood of Bavdhan (Bāvdhān)"
            ), (
                # For region with latin code similar to local code and minus a prefix or a suffix,
                # value is expected to be both latin code with the local code.
                dict(latin_code="Bavdhan", latin_name="", local_code="Bāvdhān Locality"),
                "Bavdhan (Bāvdhān Locality)"
            ), (
                # For region with both latin code and name, and both local code and name,
                # value is expected to be both latin name with the local name.
                dict(latin_code="BH5", latin_name="Bhosari", local_code="05", local_name="भोसरी"),
                "Bhosari (भोसरी)"
            )
        ]
        for kwargs, expected_value in test_data:
            for esperanto_on, esperanto_name in product((False, True), ("", "Najbarejo", "Bavdhan")):
                with self.subTest(**kwargs, esperanto=esperanto_name, include_esperanto=esperanto_on):
                    region = CountryRegionFactory.build(**kwargs, esperanto_name=esperanto_name)
                    self.assertEqual(
                        region.get_display_value(with_esperanto=esperanto_on),
                        f"{esperanto_name} \xa0\u2013\xa0 {expected_value}" if esperanto_on and esperanto_name
                        else expected_value
                    )

        # The value is expected to be calculated only once and memoized.
        region = CountryRegionFactory.build(short_code=False)
        with patch('hosting.models.CountryRegion.latin_code', new_callable=PropertyMock) as mock_name:
            result1 = region.get_display_value()
            result2 = region.get_display_value()
            mock_name.assert_called_once()
            self.assertEqual(id(result1), id(result2))
            region.latin_code = "Charholi Budruk"
            mock_name.reset_mock()
            result3 = region.get_display_value()
            mock_name.assert_not_called()
            self.assertEqual(id(result1), id(result3))

            result4 = region.get_display_value(with_esperanto=True)
            mock_name.assert_called_once()
            self.assertNotEqual(id(result1), id(result4))

    def test_str(self):
        region = CountryRegionFactory.build(short_code=False)
        self.assertEqual(
            str(region),
            f"{region.country.code}: {region.latin_code}"
        )
        region = CountryRegionFactory.build(short_code=True)
        self.assertEqual(
            str(region),
            f"{region.country.code}: {region.latin_name} ({region.latin_code})"
        )
