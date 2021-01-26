from unittest.mock import PropertyMock, patch

from django.test import TestCase, tag

from ..factories import CountryRegionFactory


@tag('models', 'subregions')
class CountryRegionModelTests(TestCase):
    def test_field_max_lengths(self):
        region = CountryRegionFactory.build()
        self.assertEquals(region._meta.get_field('iso_code').max_length, 4)
        self.assertEquals(region._meta.get_field('latin_code').max_length, 70)
        self.assertEquals(region._meta.get_field('latin_name').max_length, 70)
        self.assertEquals(region._meta.get_field('local_code').max_length, 70)
        self.assertEquals(region._meta.get_field('local_name').max_length, 70)
        self.assertEquals(region._meta.get_field('esperanto_name').max_length, 70)

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
                dict(latin_code="Bavdhan", latin_name="", local_code="Bavdhan Localilty"),
                "Bavdhan Localilty"
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
            for esperanto_name in ("", "Najbarejo"):
                with self.subTest(**kwargs, esperanto=esperanto_name):
                    region = CountryRegionFactory.build(**kwargs, esperanto_name=esperanto_name)
                    if esperanto_name:
                        self.assertEqual(
                            region.get_display_value(),
                            f"{esperanto_name} \xa0\u2013\xa0 {expected_value}"
                        )
                    else:
                        self.assertEqual(region.get_display_value(), expected_value)

        # The value is expected to be calculated only once and memoized.
        region = CountryRegionFactory.build(short_code=False)
        with patch('hosting.models.CountryRegion.latin_code', new_callable=PropertyMock) as mock_name:
            result1 = region.get_display_value()
            result2 = region.get_display_value()
            mock_name.assert_called_once()
            self.assertEqual(id(result1), id(result2))
            region.latin_name = "Charholi Budruk"
            result3 = region.get_display_value()
            mock_name.assert_called_once()
            self.assertEqual(id(result1), id(result3))

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
