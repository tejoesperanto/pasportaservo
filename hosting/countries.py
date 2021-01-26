"""
This file contains a dictionary of various metadata as well as administrative
divisions for the countries defined by the "django_countries" module. To update
the data, use the `update_countries_metadata` management command.

The bulk of the data is coming from the "addressing" PHP library, MIT-licensed,
copyright (c) 2014-2019 Bojan Zivanovic and contributors. It is complemented by
information from GeoNames under the CC BY 4.0 license.
"""

from django.utils.translation import pgettext_lazy

COUNTRIES_DATA = {
    "AD": {
        "local_name": "Andorra",
        "languages": [
            "ca"
        ],
        "population": 77006,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "AD[1-7]0\\d",
        "postcode_format": "AD###"
    },
    "AE": {
        "local_name": "al-ʾImārāt al-ʿArabīyah al-Muttaḥidah / الإمارات العربية المتحدة",
        "languages": [
            "ar-AE",
            "fa",
            "en",
            "hi",
            "ur"
        ],
        "population": 9630959,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%administrativeArea",
        "required_fields": [
            "addressLine1",
            "administrativeArea"
        ],
        "administrative_area_type": "emirate",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "AF": {
        "local_name": "Afġānistān / افغانستان",
        "languages": [
            "fa-AF",
            "ps",
            "uz-AF",
            "tk"
        ],
        "population": 37172386,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "AG": {
        "local_name": "Antigua and Barbuda",
        "languages": [
            "en-AG"
        ],
        "population": 96286,
        "required_fields": [
            "addressLine1"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "AI": {
        "local_name": "Anguilla",
        "languages": [
            "en-AI"
        ],
        "population": 13254,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "postcode_regex": "(?:AI-)?2640",
        "postcode_format": "AI-2640"
    },
    "AL": {
        "local_name": "Shqipëria",
        "languages": [
            "sq",
            "el"
        ],
        "population": 2866376,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode\\n%locality",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "AM": {
        "local_name": "Hayastan / Հայաստան",
        "languages": [
            "hy"
        ],
        "population": 2951776,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode\\n%locality\\n%administrativeArea",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "(?:37)?\\d{4}",
        "postcode_format": "######"
    },
    "AO": {
        "local_name": "Angola",
        "languages": [
            "pt-AO"
        ],
        "population": 30809762,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "AQ": {
        "local_name": "Antarctica",
        "languages": [
            ""
        ],
        "population": 0,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "AR": {
        "local_name": "Argentina",
        "languages": [
            "es-AR",
            "en",
            "it",
            "de",
            "fr",
            "gn"
        ],
        "population": 44494502,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality\\n%administrativeArea",
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "((?:[A-HJ-NP-Z])?\\d{4})([A-Z]{3})?",
        "postcode_format": "@####@@@"
    },
    "AS": {
        "local_name": "American Samoa",
        "languages": [
            "en-AS",
            "sm",
            "to"
        ],
        "population": 55465,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea"
        ],
        "administrative_area_type": "district",
        "administrative_area_code": "ADM1",
        "postal_code_type": "zip",
        "postcode_regex": "(96799)(?:[ \\-](\\d{4}))?",
        "postcode_format": "#####-####"
    },
    "AT": {
        "local_name": "Österreich",
        "languages": [
            "de-AT",
            "hr",
            "hu",
            "sl"
        ],
        "population": 8847037,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_type": "federal state",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "AU": {
        "local_name": "Australia",
        "languages": [
            "en-AU"
        ],
        "population": 24992369,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "locality_type": "suburb",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "AW": {
        "local_name": "Aruba",
        "languages": [
            "nl-AW",
            "pap",
            "es",
            "en"
        ],
        "population": 105845,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "AX": {
        "local_name": "Åland",
        "languages": [
            "sv-AX"
        ],
        "population": 26711,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "postal_code_prefix": "AX-",
        "postcode_regex": "22\\d{3}",
        "postcode_format": "#####"
    },
    "AZ": {
        "local_name": "Azərbaycan",
        "languages": [
            "az",
            "ru",
            "hy"
        ],
        "population": 9942334,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_code": "ADM2",
        "postal_code_prefix": "AZ ",
        "postcode_regex": "\\d{4}",
        "postcode_format": "AZ ####"
    },
    "BA": {
        "local_name": "Bosna i Hercegovina – Босна и Херцеговина",
        "languages": [
            "bs",
            "hr-BA",
            "sr-BA"
        ],
        "region_language": {
            "BIH": "bs",
            "SRP": "sr-BA"
        },
        "toponym_locale": "bs",
        "population": 3323929,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_type": "entity",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "BB": {
        "local_name": "Barbados",
        "languages": [
            "en-BB"
        ],
        "population": 286641,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea %postalCode",
        "administrative_area_type": "parish",
        "postcode_regex": "BB\\d{5}",
        "postcode_format": "BB#####"
    },
    "BD": {
        "local_name": "Bangladesh / বাংলাদেশ",
        "languages": [
            "bn-BD",
            "en"
        ],
        "population": 161356039,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality - %postalCode",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "BE": {
        "local_name": "België – Belgique – Belgien",
        "languages": [
            "nl-BE",
            "fr-BE",
            "de-BE"
        ],
        "region_language": {
            "VLG": "nl-BE",
            "WAL": "fr-BE",
            "BRU": ""
        },
        "population": 11422068,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "BF": {
        "local_name": "Burkina Faso",
        "languages": [
            "fr-BF",
            "mos"
        ],
        "population": 19751535,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %sortingCode",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "BG": {
        "local_name": "Balgariya / България",
        "languages": [
            "bg",
            "tr-BG",
            "rom"
        ],
        "population": 7000039,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_type": "oblast",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "BH": {
        "local_name": "al-Baḥrayn / البحرين",
        "languages": [
            "ar-BH",
            "en",
            "fa",
            "ur"
        ],
        "population": 1569439,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "administrative_area_type": "governorate",
        "postcode_regex": "(?:\\d|1[0-2])\\d{2}",
        "postcode_format": "####|###"
    },
    "BI": {
        "local_name": "Burundi",
        "languages": [
            "fr-BI",
            "rn"
        ],
        "population": 11175378,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "BJ": {
        "local_name": "Bénin",
        "languages": [
            "fr-BJ"
        ],
        "population": 11485048,
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "BL": {
        "local_name": "Saint Barthélemy",
        "languages": [
            "fr"
        ],
        "population": 8450,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "9[78][01]\\d{2}",
        "postcode_format": "#####"
    },
    "BM": {
        "local_name": "Bermuda",
        "languages": [
            "en-BM",
            "pt"
        ],
        "population": 63968,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "[A-Z]{2} ?[A-Z0-9]{2}",
        "postcode_format": "@@ ##"
    },
    "BN": {
        "local_name": "Brunei Darussalam – بروني دارالسلام",
        "languages": [
            "ms-BN",
            "en-BN"
        ],
        "population": 428962,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "[A-Z]{2} ?\\d{4}",
        "postcode_format": "@@####"
    },
    "BO": {
        "local_name": "Bolivia",
        "languages": [
            "es-BO",
            "qu",
            "ay"
        ],
        "population": 11353142,
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "BQ": {
        "population": 18012,
        "languages": [
            "nl",
            "pap",
            "en"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "BR": {
        "local_name": "Brasil",
        "languages": [
            "pt-BR",
            "es",
            "en",
            "fr"
        ],
        "population": 209469333,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%locality-%administrativeArea\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "administrativeArea",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "dependent_locality_type": "neighborhood",
        "subdivision_depth": 2,
        "postcode_regex": "\\d{5}-?\\d{3}",
        "postcode_format": "#####-###"
    },
    "BS": {
        "local_name": "Bahamas",
        "languages": [
            "en-BS"
        ],
        "population": 385640,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea",
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "BT": {
        "local_name": "Druk Yul / འབྲུག་ཡུལ་",
        "languages": [
            "dz"
        ],
        "population": 754394,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "BV": {
        "local_name": "Bouvet-øya",
        "languages": [
            "no"
        ],
        "population": 0,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "BW": {
        "local_name": "Botswana",
        "languages": [
            "en-BW",
            "tn-BW"
        ],
        "population": 2254126,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "BY": {
        "local_name": "Belarus / Беларусь",
        "languages": [
            "be",
            "ru"
        ],
        "population": 9485386,
        "format": "%administrativeArea\\n%postalCode %locality\\n%addressLine1\\n%addressLine2\\n%organization\\n%givenName %familyName",
        "administrative_area_type": "oblast",
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "BZ": {
        "local_name": "Belize",
        "languages": [
            "en-BZ",
            "es"
        ],
        "population": 383071,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "CA": {
        "local_name": "Canada",
        "languages": [
            "en-CA",
            "fr-CA",
            "iu"
        ],
        "population": 37058856,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "[ABCEGHJKLMNPRSTVXY]\\d[ABCEGHJ-NPRSTV-Z] ?\\d[ABCEGHJ-NPRSTV-Z]\\d",
        "postcode_format": "@#@ #@#"
    },
    "CC": {
        "local_name": "Pulu Kokos (Keeling)",
        "languages": [
            "ms-CC",
            "en"
        ],
        "population": 628,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "postcode_regex": "6799",
        "postcode_format": "6799"
    },
    "CD": {
        "local_name": "République Démocratique du Congo",
        "languages": [
            "fr-CD",
            "ln",
            "ktu",
            "kg",
            "sw",
            "lua"
        ],
        "population": 84068091,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "CF": {
        "local_name": "Centrafrique",
        "languages": [
            "fr-CF",
            "sg",
            "ln",
            "kg"
        ],
        "population": 4666377,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "CG": {
        "local_name": "République du Congo",
        "languages": [
            "fr-CG",
            "kg",
            "ln-CG"
        ],
        "population": 5244363,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "CH": {
        "local_name": "Schweiz – Suisse – Svizzera – Svizra",
        "languages": [
            "de-CH",
            "fr-CH",
            "it-CH",
            "rm"
        ],
        "population": 8516543,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [],
        "administrative_area_code": "ADM1",
        "postal_code_prefix": "CH-",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "CI": {
        "local_name": "Côte d'Ivoire",
        "languages": [
            "fr-CI"
        ],
        "population": 25069229,
        "format": "%givenName %familyName\\n%organization\\n%sortingCode %addressLine1\\n%addressLine2 %locality %sortingCode",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "CK": {
        "local_name": "Cook Islands",
        "languages": [
            "en-CK",
            "mi"
        ],
        "population": 21388,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "CL": {
        "local_name": "Chile",
        "languages": [
            "es-CL"
        ],
        "population": 18729160,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality\\n%administrativeArea",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 2,
        "postcode_regex": "\\d{7}",
        "postcode_format": "#######"
    },
    "CM": {
        "local_name": "Cameroon – Cameroun",
        "languages": [
            "en-CM",
            "fr-CM"
        ],
        "population": 25216237,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "CN": {
        "local_name": "Zhōngguó / 中国",
        "languages": [
            "zh-CN",
            "yue",
            "wuu",
            "dta",
            "ug",
            "za"
        ],
        "population": 1392730000,
        "locale": "zh-Hans",
        "format": "%familyName %givenName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%locality\\n%administrativeArea, %postalCode",
        "local_format": "%postalCode\\n%administrativeArea%locality%dependentLocality\\n%addressLine1\\n%addressLine2\\n%organization\\n%familyName %givenName",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "dependent_locality_type": "district",
        "subdivision_depth": 3,
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "CO": {
        "local_name": "Colombia",
        "languages": [
            "es-CO"
        ],
        "population": 49648685,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea, %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "administrative_area_type": "department",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "CR": {
        "local_name": "Costa Rica",
        "languages": [
            "es-CR",
            "en"
        ],
        "population": 4999441,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%administrativeArea, %locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4,5}|\\d{3}-\\d{4}",
        "postcode_format": "#####"
    },
    "CU": {
        "local_name": "Cuba",
        "languages": [
            "es-CU",
            "pap"
        ],
        "population": 11338138,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea\\n%postalCode",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "CP #####"
    },
    "CV": {
        "local_name": "Cabo Verde",
        "languages": [
            "pt-CV"
        ],
        "population": 543767,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality\\n%administrativeArea",
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "CW": {
        "population": 159849,
        "languages": [
            "nl",
            "pap"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "CX": {
        "local_name": "Christmas Island",
        "languages": [
            "en",
            "zh",
            "ms-CC"
        ],
        "population": 1500,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "postcode_regex": "6798",
        "postcode_format": "6798"
    },
    "CY": {
        "local_name": "Kipros / Κύπρος – Kıbrıs",
        "languages": [
            "el-CY",
            "tr-CY",
            "en"
        ],
        "population": 1189265,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "CZ": {
        "local_name": "Česká republika",
        "languages": [
            "cs",
            "sk"
        ],
        "population": 10625695,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "postcode_regex": "\\d{3} ?\\d{2}",
        "postcode_format": "### ##"
    },
    "DE": {
        "local_name": "Deutschland",
        "languages": [
            "de"
        ],
        "toponym_locale": "de",
        "population": 82927922,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_type": "federal state",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "DJ": {
        "local_name": "Djibouti / جيبوتي",
        "languages": [
            "fr-DJ",
            "ar",
            "so-DJ",
            "aa"
        ],
        "population": 958920,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "DK": {
        "local_name": "Danmark",
        "languages": [
            "da-DK",
            "en",
            "fo",
            "de-DK"
        ],
        "population": 5797446,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "DM": {
        "local_name": "Dominica",
        "languages": [
            "en-DM"
        ],
        "population": 71625,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "DO": {
        "local_name": "República Dominicana",
        "languages": [
            "es-DO"
        ],
        "population": 10627165,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "DZ": {
        "local_name": "al-Jazā'ir / الجزائر",
        "languages": [
            "ar-DZ"
        ],
        "population": 42228429,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "EC": {
        "local_name": "Ecuador",
        "languages": [
            "es-EC"
        ],
        "population": 17084357,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode\\n%locality",
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "EE": {
        "local_name": "Eesti",
        "languages": [
            "et",
            "ru"
        ],
        "population": 1320884,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_type": "county",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "EG": {
        "local_name": "Miṣr / مصر",
        "languages": [
            "ar-EG",
            "en",
            "fr"
        ],
        "population": 98423595,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea\\n%postalCode",
        "administrative_area_type": "governorate",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "EH": {
        "local_name": "aṣ-Ṣaḥrā' al-Gharbiyyah / الصحراء الغربية",
        "languages": [
            "ar",
            "mey"
        ],
        "population": 273008,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "ER": {
        "local_name": "Eritrea",
        "languages": [
            "aa-ER",
            "ar",
            "tig",
            "kun",
            "ti-ER"
        ],
        "population": 0,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "ES": {
        "local_name": "España",
        "languages": [
            "es-ES",
            "ca",
            "gl",
            "eu",
            "oc"
        ],
        "population": 46723749,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM2",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "ET": {
        "local_name": "Itiyoophiyaa / ኢትዮጵያ",
        "languages": [
            "am",
            "en-ET",
            "om-ET",
            "ti-ET",
            "so-ET",
            "sid"
        ],
        "toponym_locale": "am",
        "population": 109224559,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "FI": {
        "local_name": "Suomi",
        "languages": [
            "fi-FI",
            "sv-FI",
            "smn"
        ],
        "toponym_locale": "fi",
        "population": 5518050,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "postal_code_prefix": "FI-",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "FJ": {
        "local_name": "Fiji",
        "languages": [
            "en-FJ",
            "fj"
        ],
        "population": 883483,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "FK": {
        "local_name": "Falkland Islands",
        "languages": [
            "en-FK"
        ],
        "population": 2638,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "FIQQ 1ZZ",
        "postcode_format": "FIQQ 1ZZ"
    },
    "FM": {
        "local_name": "Micronesia",
        "languages": [
            "en-FM",
            "chk",
            "pon",
            "yap",
            "kos",
            "uli",
            "woe",
            "nkr",
            "kpg"
        ],
        "population": 112640,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "postal_code_type": "zip",
        "postcode_regex": "(9694[1-4])(?:[ \\-](\\d{4}))?",
        "postcode_format": "#####"
    },
    "FO": {
        "local_name": "Føroyar – Færøerne",
        "languages": [
            "fo",
            "da-FO"
        ],
        "population": 48497,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postal_code_prefix": "FO",
        "postcode_regex": "\\d{3}",
        "postcode_format": "###"
    },
    "FR": {
        "local_name": "France",
        "languages": [
            "fr-FR",
            "frp",
            "br",
            "co",
            "ca",
            "eu",
            "oc"
        ],
        "region_language": {
            "ARA": "oc",
            "BFC": "frp",
            "BRE": "br",
            "20R": "co",
            "NOR": "nrf",
            "NAQ": "oc",
            "OCC": "oc",
            "PDL": "br",
            "PAC": "oc"
        },
        "population": 66987244,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "sortingCode"
        ],
        "administrative_area_type": "region",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{2} ?\\d{3}",
        "postcode_format": "#####"
    },
    "GA": {
        "local_name": "Gabon",
        "languages": [
            "fr-GA"
        ],
        "population": 2119275,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "GB": {
        "local_name": "United Kingdom",
        "languages": [
            "en-GB",
            "cy-GB",
            "gd"
        ],
        "population": 66488991,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "administrative_area_type": "country",
        "administrative_area_code": "ADM1",
        "locality_type": "post_town",
        "postcode_regex": "GIR ?0AA|(?:(?:AB|AL|B|BA|BB|BD|BF|BH|BL|BN|BR|BS|BT|BX|CA|CB|CF|CH|CM|CO|CR|CT|CV|CW|DA|DD|DE|DG|DH|DL|DN|DT|DY|E|EC|EH|EN|EX|FK|FY|G|GL|GY|GU|HA|HD|HG|HP|HR|HS|HU|HX|IG|IM|IP|IV|JE|KA|KT|KW|KY|L|LA|LD|LE|LL|LN|LS|LU|M|ME|MK|ML|N|NE|NG|NN|NP|NR|NW|OL|OX|PA|PE|PH|PL|PO|PR|RG|RH|RM|S|SA|SE|SG|SK|SL|SM|SN|SO|SP|SR|SS|ST|SW|SY|TA|TD|TF|TN|TQ|TR|TS|TW|UB|W|WA|WC|WD|WF|WN|WR|WS|WV|YO|ZE)(?:\\d[\\dA-Z]? ?\\d[ABD-HJLN-UW-Z]{2}))|BFPO ?\\d{1,4}",
        "postcode_format": "@# #@@|@## #@@|@@# #@@|@@## #@@|@#@ #@@|@@#@ #@@|GIR0AA"
    },
    "GD": {
        "local_name": "Grenada",
        "languages": [
            "en-GD"
        ],
        "population": 111454,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "GE": {
        "local_name": "Sakartvelo / საქართველო",
        "languages": [
            "ka",
            "ru",
            "hy",
            "az"
        ],
        "region_language": {
            "AB": "ab"
        },
        "population": 3731000,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "GF": {
        "local_name": "Guyane Française",
        "languages": [
            "fr-GF"
        ],
        "population": 195506,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "9[78]3\\d{2}",
        "postcode_format": "#####"
    },
    "GG": {
        "local_name": "Guernsey",
        "languages": [
            "en",
            "nrf"
        ],
        "population": 65228,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "GY\\d[\\dA-Z]? ?\\d[ABD-HJLN-UW-Z]{2}",
        "postcode_format": "GY# #@@|GY## #@@"
    },
    "GH": {
        "local_name": "Ghana",
        "languages": [
            "en-GH",
            "ak",
            "ee",
            "tw"
        ],
        "population": 29767108,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "GI": {
        "local_name": "Gibraltar",
        "languages": [
            "en-GI",
            "es",
            "it",
            "pt"
        ],
        "population": 33718,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode",
        "required_fields": [
            "addressLine1"
        ],
        "postcode_regex": "GX11 1AA",
        "postcode_format": "GX11 1AA"
    },
    "GL": {
        "local_name": "Kalaallit Nunaat – Grønland",
        "languages": [
            "kl",
            "da-GL",
            "en"
        ],
        "population": 56025,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "postcode_regex": "39\\d{2}",
        "postcode_format": "####"
    },
    "GM": {
        "local_name": "The Gambia",
        "languages": [
            "en-GM",
            "mnk",
            "wof",
            "wo",
            "ff"
        ],
        "population": 2280102,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "GN": {
        "local_name": "Guinée",
        "languages": [
            "fr-GN"
        ],
        "population": 12414318,
        "format": "%givenName %familyName\\n%organization\\n%postalCode %addressLine1\\n%addressLine2 %locality",
        "postcode_regex": "\\d{3}",
        "postcode_format": "###"
    },
    "GP": {
        "local_name": "Guadeloupe",
        "languages": [
            "fr-GP"
        ],
        "population": 443000,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "9[78][01]\\d{2}",
        "postcode_format": "#####"
    },
    "GQ": {
        "local_name": "Equatorial Guinea",
        "languages": [
            "es-GQ",
            "fr"
        ],
        "population": 1308974,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "GR": {
        "local_name": "Ellada / Ελλάδα",
        "languages": [
            "el-GR",
            "en",
            "fr"
        ],
        "toponym_locale": "DECODE",
        "population": 10727668,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{3} ?\\d{2}",
        "postcode_format": "### ##"
    },
    "GS": {
        "local_name": "South Georgia and South Sandwich Islands",
        "languages": [
            "en"
        ],
        "population": 30,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "SIQQ 1ZZ",
        "postcode_format": "SIQQ 1ZZ"
    },
    "GT": {
        "local_name": "Guatemala",
        "languages": [
            "es-GT"
        ],
        "population": 17247807,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode- %locality",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "GU": {
        "local_name": "Guam",
        "languages": [
            "en-GU",
            "ch-GU"
        ],
        "population": 165768,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization"
        ],
        "postal_code_type": "zip",
        "postcode_regex": "(969(?:[12]\\d|3[12]))(?:[ \\-](\\d{4}))?",
        "postcode_format": "969##"
    },
    "GW": {
        "local_name": "Guiné-Bissau",
        "languages": [
            "pt-GW",
            "pov"
        ],
        "population": 1874309,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "GY": {
        "local_name": "Guyana",
        "languages": [
            "en-GY"
        ],
        "population": 779004,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "HK": {
        "local_name": "Hong Kong / 香港",
        "languages": [
            "zh-HK",
            "yue",
            "zh",
            "en"
        ],
        "population": 7451000,
        "locale": "zh-Hant",
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea",
        "local_format": "%administrativeArea\\n%locality\\n%addressLine1\\n%addressLine2\\n%organization\\n%givenName %familyName",
        "required_fields": [
            "addressLine1",
            "administrativeArea"
        ],
        "uppercase_fields": [
            "administrativeArea"
        ],
        "administrative_area_type": "area",
        "locality_type": "district",
        "subdivision_depth": 2,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "HM": {
        "local_name": "Heard Island and McDonald Islands",
        "languages": [
            "en"
        ],
        "population": 0,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "HN": {
        "local_name": "Honduras",
        "languages": [
            "es-HN",
            "cab",
            "miq"
        ],
        "population": 9587522,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "department",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "HR": {
        "local_name": "Hrvatska",
        "languages": [
            "hr-HR",
            "sr"
        ],
        "population": 4089400,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postal_code_prefix": "HR-",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "HT": {
        "local_name": "Haiti",
        "languages": [
            "ht",
            "fr-HT"
        ],
        "population": 11123176,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postal_code_prefix": "HT",
        "postcode_regex": "\\d{4}",
        "postcode_format": "HT####"
    },
    "HU": {
        "local_name": "Magyarország",
        "languages": [
            "hu-HU"
        ],
        "population": 9768785,
        "format": "%familyName %givenName\\n%organization\\n%locality\\n%addressLine1\\n%addressLine2\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization"
        ],
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "ID": {
        "local_name": "Indonesia",
        "languages": [
            "id",
            "en",
            "nl",
            "jv"
        ],
        "population": 267663435,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "IE": {
        "local_name": "Ireland – Éire",
        "languages": [
            "en-IE",
            "ga-IE"
        ],
        "population": 4853506,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%locality\\n%administrativeArea\\n%postalCode",
        "administrative_area_type": "county",
        "administrative_area_code": "ADM1",
        "dependent_locality_type": "townland",
        "subdivision_depth": 1,
        "postal_code_type": "eircode",
        "postcode_regex": "[\\dA-Z]{3} ?[\\dA-Z]{4}",
        "postcode_format": "@@@ @@@@"
    },
    "IL": {
        "local_name": "Israel / ישראל",
        "languages": [
            "he",
            "ar-IL",
            "en-IL"
        ],
        "population": 8883800,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "\\d{5}(?:\\d{2})?",
        "postcode_format": "#######"
    },
    "IM": {
        "local_name": "Isle of Man – Ellan Vannin",
        "languages": [
            "en",
            "gv"
        ],
        "population": 84077,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "IM\\d[\\dA-Z]? ?\\d[ABD-HJLN-UW-Z]{2}",
        "postcode_format": "IM# #@@|IM## #@@"
    },
    "IN": {
        "local_name": "Bhārat / भारत",
        "languages": [
            "en-IN",
            "hi",
            "bn",
            "te",
            "mr",
            "ta",
            "ur",
            "gu",
            "kn",
            "ml",
            "or",
            "pa",
            "as",
            "bh",
            "sat",
            "ks",
            "ne",
            "sd",
            "kok",
            "doi",
            "mni",
            "sit",
            "sa",
            "fr",
            "lus",
            "inc"
        ],
        "population": 1352617328,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode\\n%administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postal_code_type": "pin",
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "IO": {
        "local_name": "British Indian Ocean Territory",
        "languages": [
            "en-IO"
        ],
        "population": 4000,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "BBND 1ZZ",
        "postcode_format": "BBND 1ZZ"
    },
    "IQ": {
        "local_name": "Iraq / ٱلْعِرَاق‎ – عێراق‎",
        "languages": [
            "ar-IQ",
            "ku",
            "hy"
        ],
        "population": 38433600,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "governorate",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "IR": {
        "local_name": "Iran / ایران‎",
        "languages": [
            "fa-IR",
            "ku"
        ],
        "toponym_locale": "phon",
        "population": 81800269,
        "format": "%organization\\n%givenName %familyName\\n%administrativeArea\\n%locality, %dependentLocality\\n%addressLine1\\n%addressLine2\\n%postalCode",
        "administrative_area_code": "ADM1",
        "dependent_locality_type": "neighborhood",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}-?\\d{5}",
        "postcode_format": "##########"
    },
    "IS": {
        "local_name": "Ísland",
        "languages": [
            "is",
            "en",
            "de",
            "da",
            "sv",
            "no"
        ],
        "population": 353574,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{3}",
        "postcode_format": "###"
    },
    "IT": {
        "local_name": "Italia",
        "languages": [
            "it-IT",
            "de-IT",
            "fr-IT",
            "sc",
            "ca",
            "co",
            "sl"
        ],
        "population": 60431283,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM2",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "JE": {
        "local_name": "Jersey",
        "languages": [
            "en",
            "fr",
            "nrf"
        ],
        "population": 90812,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "JE\\d[\\dA-Z]? ?\\d[ABD-HJLN-UW-Z]{2}",
        "postcode_format": "JE# #@@|JE## #@@"
    },
    "JM": {
        "local_name": "Jamaica",
        "languages": [
            "en-JM"
        ],
        "population": 2934855,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "administrative_area_type": "parish",
        "subdivision_depth": 1,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "JO": {
        "local_name": "al-ʾUrdunn / الأُرْدُن",
        "languages": [
            "ar-JO",
            "en"
        ],
        "population": 9956011,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "administrative_area_type": "governorate",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "JP": {
        "local_name": "Nippon / 日本",
        "languages": [
            "ja"
        ],
        "population": 126529100,
        "locale": "ja",
        "format": "%familyName %givenName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea\\n%postalCode",
        "local_format": "〒%postalCode\\n%administrativeArea%locality\\n%addressLine1\\n%addressLine2\\n%organization\\n%familyName %givenName",
        "required_fields": [
            "addressLine1",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "administrative_area_type": "prefecture",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{3}-?\\d{4}",
        "postcode_format": "###-####"
    },
    "KE": {
        "local_name": "Kenya",
        "languages": [
            "en-KE",
            "sw-KE"
        ],
        "population": 51393010,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "KG": {
        "local_name": "Qırğızstan / Кыргызстан",
        "languages": [
            "ky",
            "uz",
            "ru"
        ],
        "population": 6315800,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_type": "oblast",
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "KH": {
        "local_name": "Kampuchea / កម្ពុជា",
        "languages": [
            "km",
            "fr",
            "en"
        ],
        "population": 16249798,
        "format": "%familyName %givenName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "KI": {
        "local_name": "Kiribati",
        "languages": [
            "en-KI",
            "gil"
        ],
        "population": 115847,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%administrativeArea\\n%locality",
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "KM": {
        "local_name": "Comores – ﺍﻟﻘﻤﺮي – Komori",
        "languages": [
            "ar",
            "fr-KM"
        ],
        "population": 832322,
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality"
        ],
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "KN": {
        "local_name": "Saint Kitts and Nevis",
        "languages": [
            "en-KN"
        ],
        "population": 52441,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "KP": {
        "local_name": "Pukchosŏn / 북조선",
        "languages": [
            "ko-KP"
        ],
        "population": 25549819,
        "locale": "ko",
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea, %postalCode",
        "local_format": "%postalCode\\n%administrativeArea\\n%locality\\n%addressLine1\\n%addressLine2\\n%organization\\n%givenName %familyName",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "(\\d{6})",
        "postcode_format": "###-###"
    },
    "KR": {
        "local_name": "Hanguk / 한국",
        "languages": [
            "ko-KR",
            "en"
        ],
        "population": 51635256,
        "locale": "ko",
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%locality\\n%administrativeArea\\n%postalCode",
        "local_format": "%administrativeArea %locality%dependentLocality\\n%addressLine1\\n%addressLine2\\n%organization\\n%givenName %familyName\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "postalCode"
        ],
        "administrative_area_type": "do_si",
        "administrative_area_code": "ADM1",
        "dependent_locality_type": "district",
        "subdivision_depth": 3,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "KW": {
        "local_name": "Kuwait / الكويت",
        "languages": [
            "ar-KW",
            "en"
        ],
        "population": 4137309,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_type": "governorate",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "KY": {
        "local_name": "Cayman Islands",
        "languages": [
            "en-KY"
        ],
        "population": 64174,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "subdivision_depth": 1,
        "postcode_regex": "KY\\d-\\d{4}",
        "postcode_format": "KY#-####"
    },
    "KZ": {
        "local_name": "Qazaqstan / Қазақстан",
        "languages": [
            "kk",
            "ru"
        ],
        "population": 18276499,
        "format": "%postalCode\\n%administrativeArea\\n%locality\\n%addressLine1\\n%addressLine2\\n%organization\\n%givenName %familyName",
        "administrative_area_type": "oblast",
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "LA": {
        "local_name": "Lāo / ລາວ",
        "languages": [
            "lo",
            "fr",
            "en"
        ],
        "population": 7061507,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "LB": {
        "local_name": "Lubnān / لبنان‎",
        "languages": [
            "ar-LB",
            "fr-LB",
            "en",
            "hy"
        ],
        "population": 6848925,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "administrative_area_type": "governorate",
        "postcode_regex": "(?:\\d{4})(?: ?(?:\\d{4}))?",
        "postcode_format": "#### ####|####"
    },
    "LC": {
        "local_name": "Saint Lucia",
        "languages": [
            "en-LC"
        ],
        "population": 181889,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "LI": {
        "local_name": "Liechtenstein",
        "languages": [
            "de-LI"
        ],
        "population": 37910,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "postal_code_prefix": "FL-",
        "postcode_regex": "948[5-9]|949[0-8]",
        "postcode_format": "####"
    },
    "LK": {
        "local_name": "Śrī Laṅkā / ශ්‍රී ලංකා – Ilaṅkai / இலங்கை",
        "languages": [
            "si",
            "ta",
            "en"
        ],
        "toponym_locale": "phon",
        "population": 21670000,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "LR": {
        "local_name": "Liberia",
        "languages": [
            "en-LR"
        ],
        "population": 4818977,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "LS": {
        "local_name": "Lesotho",
        "languages": [
            "en-LS",
            "st",
            "zu",
            "xh"
        ],
        "population": 2108132,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "\\d{3}",
        "postcode_format": "###"
    },
    "LT": {
        "local_name": "Lietuva",
        "languages": [
            "lt",
            "ru",
            "pl"
        ],
        "population": 2789533,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_type": "county",
        "postal_code_prefix": "LT-",
        "postcode_regex": "\\d{5}",
        "postcode_format": "LT-#####"
    },
    "LU": {
        "local_name": "Lëtzebuerg – Luxemburg – Luxembourg",
        "languages": [
            "lb",
            "de-LU",
            "fr-LU"
        ],
        "population": 607728,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "postal_code_prefix": "L-",
        "postcode_regex": "\\d{4}",
        "postcode_format": "L-####"
    },
    "LV": {
        "local_name": "Latvija",
        "languages": [
            "lv",
            "ru",
            "lt"
        ],
        "population": 1926542,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "postcode_regex": "LV-\\d{4}",
        "postcode_format": "LV-####"
    },
    "LY": {
        "local_name": "Lībiyā / ليبيا",
        "languages": [
            "ar-LY",
            "it",
            "en"
        ],
        "population": 6678567,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "MA": {
        "local_name": "al-Maḡrib / المغرب‎",
        "languages": [
            "ar-MA",
            "ber",
            "fr"
        ],
        "population": 36029138,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "MC": {
        "local_name": "Monaco",
        "languages": [
            "fr-MC",
            "en",
            "it"
        ],
        "population": 38682,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "postal_code_prefix": "MC-",
        "postcode_regex": "980\\d{2}",
        "postcode_format": "#####"
    },
    "MD": {
        "local_name": "Moldova",
        "languages": [
            "ro",
            "ru",
            "gag",
            "tr"
        ],
        "population": 3545883,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_code": "ADM1",
        "postal_code_prefix": "MD-",
        "postcode_regex": "\\d{4}",
        "postcode_format": "MD-####"
    },
    "ME": {
        "local_name": "Crna Gora / Црна Гора",
        "languages": [
            "sr",
            "hu",
            "bs",
            "sq",
            "hr",
            "rom"
        ],
        "population": 622345,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "8\\d{4}",
        "postcode_format": "#####"
    },
    "MF": {
        "local_name": "Saint Martin",
        "languages": [
            "fr"
        ],
        "population": 37264,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "9[78][01]\\d{2}",
        "postcode_format": "#####"
    },
    "MG": {
        "local_name": "Madagasikara",
        "languages": [
            "fr-MG",
            "mg"
        ],
        "population": 26262368,
        "format": "%familyName %givenName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{3}",
        "postcode_format": "###"
    },
    "MH": {
        "local_name": "Marshall Islands",
        "languages": [
            "mh",
            "en-MH"
        ],
        "population": 58413,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "postal_code_type": "zip",
        "postcode_regex": "(969[67]\\d)(?:[ \\-](\\d{4}))?",
        "postcode_format": "#####-####"
    },
    "MK": {
        "local_name": "Severna Makedonija / Северна Македонија – Maqedonia e Veriut",
        "languages": [
            "mk",
            "sq",
            "tr",
            "rmm",
            "sr"
        ],
        "population": 2082958,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "ML": {
        "local_name": "Mali",
        "languages": [
            "fr-ML",
            "bm"
        ],
        "population": 19077690,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "MM": {
        "local_name": "Myanmar / မြန်မာ",
        "languages": [
            "my"
        ],
        "population": 53708395,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %postalCode",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "MN": {
        "local_name": "Mongol Uls / Монгол Улс",
        "languages": [
            "mn",
            "ru"
        ],
        "population": 3170208,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea %postalCode",
        "postcode_regex": "\\d{5}",
        "postcode_format": "######"
    },
    "MO": {
        "local_name": "Macao",
        "languages": [
            "zh",
            "zh-MO",
            "pt"
        ],
        "population": 631636,
        "locale": "zh-Hans",
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2",
        "local_format": "%addressLine1\\n%addressLine2\\n%organization\\n%givenName %familyName",
        "required_fields": [
            "addressLine1"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "MP": {
        "local_name": "Northern Mariana Islands",
        "languages": [
            "fil",
            "tl",
            "zh",
            "ch-MP",
            "en-MP"
        ],
        "population": 56882,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "postal_code_type": "zip",
        "postcode_regex": "(9695[012])(?:[ \\-](\\d{4}))?",
        "postcode_format": "#####"
    },
    "MQ": {
        "local_name": "Martinique",
        "languages": [
            "fr-MQ"
        ],
        "population": 432900,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "9[78]2\\d{2}",
        "postcode_format": "#####"
    },
    "MR": {
        "local_name": "Mūrītānyā / موريتانيا",
        "languages": [
            "ar-MR",
            "fuc",
            "snk",
            "fr",
            "mey",
            "wo"
        ],
        "population": 4403319,
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "MS": {
        "local_name": "Montserrat",
        "languages": [
            "en-MS"
        ],
        "population": 9341,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "MT": {
        "local_name": "Malta",
        "languages": [
            "mt",
            "en-MT"
        ],
        "population": 483530,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "[A-Z]{3} ?\\d{2,4}",
        "postcode_format": "@@@ ####"
    },
    "MU": {
        "local_name": "Mauritius",
        "languages": [
            "en-MU",
            "bho",
            "fr"
        ],
        "population": 1265303,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode\\n%locality",
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "\\d{3}(?:\\d{2}|[A-Z]{2}\\d{3})",
        "postcode_format": "#####|###@@###"
    },
    "MV": {
        "local_name": "Dhivehi Raajje / ދިވެހިރާއްޖެ",
        "languages": [
            "dv",
            "en"
        ],
        "population": 515696,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "MW": {
        "local_name": "Malaŵi",
        "languages": [
            "ny",
            "yao",
            "tum",
            "swk"
        ],
        "population": 17563749,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %sortingCode",
        "postcode_regex": "(\\d{6})",
        "postcode_format": "######"
    },
    "MX": {
        "local_name": "México",
        "languages": [
            "es-MX"
        ],
        "population": 126190788,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%postalCode %locality, %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "dependent_locality_type": "neighborhood",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "MY": {
        "local_name": "Malaysia – مليسيا",
        "languages": [
            "ms-MY",
            "en",
            "zh",
            "ta",
            "te",
            "ml",
            "pa",
            "th"
        ],
        "population": 31528585,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%postalCode %locality\\n%administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "dependent_locality_type": "village_township",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "MZ": {
        "local_name": "Mozambique",
        "languages": [
            "pt-MZ",
            "vmw"
        ],
        "population": 29495962,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality%administrativeArea",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "NA": {
        "local_name": "Namibia",
        "languages": [
            "en-NA",
            "af",
            "de",
            "hz",
            "naq"
        ],
        "population": 2448255,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%localityn%postalCode",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "NC": {
        "local_name": "Nouvelle-Calédonie",
        "languages": [
            "fr-NC"
        ],
        "population": 284060,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "988\\d{2}",
        "postcode_format": "#####"
    },
    "NE": {
        "local_name": "Niger",
        "languages": [
            "fr-NE",
            "ha",
            "kr",
            "dje"
        ],
        "population": 22442948,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "NF": {
        "local_name": "Norfolk Island",
        "languages": [
            "en-NF"
        ],
        "population": 1828,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "postcode_regex": "2899",
        "postcode_format": "2899"
    },
    "NG": {
        "local_name": "Nigeria",
        "languages": [
            "en-NG",
            "ha",
            "yo",
            "ig",
            "ff"
        ],
        "population": 195874740,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%locality %postalCode\\n%administrativeArea",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "NI": {
        "local_name": "Nicaragua",
        "languages": [
            "es-NI",
            "en"
        ],
        "population": 6465513,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode\\n%locality, %administrativeArea",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "department",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "NL": {
        "local_name": "Nederland",
        "languages": [
            "nl-NL",
            "fy-NL"
        ],
        "population": 17231017,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4} ?[A-Z]{2}",
        "postcode_format": "#### @@"
    },
    "NO": {
        "local_name": "Norge – Noreg",
        "languages": [
            "no",
            "nb",
            "nn",
            "se",
            "fi"
        ],
        "population": 5314336,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "locality_type": "post_town",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "NP": {
        "local_name": "Nepal / नेपाल",
        "languages": [
            "ne",
            "en"
        ],
        "population": 28087871,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "NR": {
        "local_name": "Nauru",
        "languages": [
            "na",
            "en-NR"
        ],
        "population": 12704,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%administrativeArea",
        "required_fields": [
            "addressLine1",
            "administrativeArea"
        ],
        "administrative_area_type": "district",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "NU": {
        "local_name": "Niue",
        "languages": [
            "niu",
            "en-NU"
        ],
        "population": 2166,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "NZ": {
        "local_name": "New Zealand",
        "languages": [
            "en-NZ",
            "mi"
        ],
        "population": 4885500,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%locality %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "OM": {
        "local_name": "ʿUmān / عُمَان‎",
        "languages": [
            "ar-OM",
            "en",
            "bal",
            "ur"
        ],
        "population": 4829483,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode\\n%locality",
        "postcode_regex": "(?:PC )?\\d{3}",
        "postcode_format": "###"
    },
    "PA": {
        "local_name": "Panama",
        "languages": [
            "es-PA",
            "en"
        ],
        "population": 4176873,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "PE": {
        "local_name": "Peru",
        "languages": [
            "es-PE",
            "qu",
            "ay"
        ],
        "population": 31989256,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode\\n%administrativeArea",
        "administrative_area_code": "ADM1",
        "locality_type": "district",
        "subdivision_depth": 1,
        "postcode_regex": "(?:LIMA \\d{1,2}|CALLAO 0?\\d)|[0-2]\\d{4}",
        "postcode_format": "0####|1####|2####"
    },
    "PF": {
        "local_name": "Polynésie française",
        "languages": [
            "fr-PF",
            "ty"
        ],
        "region_language": {
            "I": "ty",
            "M": "ty",
            "S": "ty",
            "T": "ty",
            "V": "ty"
        },
        "population": 277679,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "postcode_regex": "987\\d{2}",
        "postcode_format": "#####"
    },
    "PG": {
        "local_name": "Papua New Guinea",
        "languages": [
            "en-PG",
            "ho",
            "meu",
            "tpi"
        ],
        "population": 8606316,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{3}",
        "postcode_format": "###"
    },
    "PH": {
        "local_name": "Pilipinas",
        "languages": [
            "tl",
            "en-PH",
            "fil",
            "ceb",
            "tgl",
            "ilo",
            "hil",
            "war",
            "pam",
            "bik",
            "bcl",
            "pag",
            "mrw",
            "tsg",
            "mdh",
            "cbk",
            "krj",
            "sgd",
            "msb",
            "akl",
            "ibg",
            "yka",
            "mta",
            "abx"
        ],
        "population": 106651922,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality, %locality\\n%postalCode %administrativeArea",
        "administrative_area_code": "ADM2",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "PK": {
        "local_name": "Pakistan / پاکستان",
        "languages": [
            "ur-PK",
            "en-PK",
            "pa",
            "sd",
            "ps",
            "brh"
        ],
        "toponym_locale": "en",
        "population": 212215030,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality-%postalCode",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "PL": {
        "local_name": "Polska",
        "languages": [
            "pl"
        ],
        "toponym_locale": "pl",
        "population": 37978548,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_type": "voivodeship",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{2}-\\d{3}",
        "postcode_format": "##-###"
    },
    "PM": {
        "local_name": "Saint-Pierre-et-Miquelon",
        "languages": [
            "fr-PM"
        ],
        "population": 7012,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "9[78]5\\d{2}",
        "postcode_format": "#####"
    },
    "PN": {
        "local_name": "Pitcairn",
        "languages": [
            "en-PN"
        ],
        "population": 46,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "PCRN 1ZZ",
        "postcode_format": "PCRN 1ZZ"
    },
    "PR": {
        "local_name": "Puerto Rico",
        "languages": [
            "en-PR",
            "es-PR"
        ],
        "population": 3195153,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization"
        ],
        "postal_code_type": "zip",
        "postal_code_prefix": "PR ",
        "postcode_regex": "(00[679]\\d{2})(?:[ \\-](\\d{4}))?",
        "postcode_format": "#####-####"
    },
    "PS": {
        "local_name": "Filasṭīn / فلسطين‎",
        "languages": [
            "ar-PS"
        ],
        "population": 4569087,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "PT": {
        "local_name": "Portugal",
        "languages": [
            "pt-PT",
            "mwl"
        ],
        "population": 10281762,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4}-\\d{3}",
        "postcode_format": "####-###"
    },
    "PW": {
        "local_name": "Palau",
        "languages": [
            "pau",
            "sov",
            "en-PW",
            "tox",
            "ja",
            "fil",
            "zh"
        ],
        "population": 17907,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "postal_code_type": "zip",
        "postcode_regex": "(969(?:39|40))(?:[ \\-](\\d{4}))?",
        "postcode_format": "96939|96939-####|96940|96940-####"
    },
    "PY": {
        "local_name": "Paraguay",
        "languages": [
            "es-PY",
            "gn"
        ],
        "population": 6956071,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "QA": {
        "local_name": "Qaṭar / قطر‎",
        "languages": [
            "ar-QA",
            "es"
        ],
        "population": 2781677,
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "RE": {
        "local_name": "Réunion",
        "languages": [
            "fr-RE"
        ],
        "population": 776948,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "9[78]4\\d{2}",
        "postcode_format": "#####"
    },
    "RO": {
        "local_name": "România",
        "languages": [
            "ro",
            "hu",
            "rom"
        ],
        "population": 19473936,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality"
        ],
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "RS": {
        "local_name": "Srbija / Србија",
        "languages": [
            "sr",
            "hu",
            "bs",
            "rom"
        ],
        "population": 6982084,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{5,6}",
        "postcode_format": "######"
    },
    "RU": {
        "local_name": "Rossiya / Россия",
        "languages": [
            "ru",
            "tt",
            "xal",
            "cau",
            "ady",
            "kv",
            "ce",
            "tyv",
            "cv",
            "udm",
            "tut",
            "mns",
            "bua",
            "myv",
            "mdf",
            "chm",
            "ba",
            "inh",
            "tut",
            "kbd",
            "krc",
            "av",
            "sah",
            "nog"
        ],
        "population": 144478050,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality"
        ],
        "administrative_area_type": "federal subject",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "RW": {
        "local_name": "Rwanda",
        "languages": [
            "rw",
            "en-RW",
            "fr-RW",
            "sw"
        ],
        "population": 12301939,
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "SA": {
        "local_name": "as-Saʿūdīyah / ٱلسَّعُوْدِيَّة‎",
        "languages": [
            "ar-SA"
        ],
        "population": 33699947,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "SB": {
        "local_name": "Solomon Islands",
        "languages": [
            "en-SB",
            "tpi"
        ],
        "population": 652858,
        "administrative_area_code": "ADM1",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "SC": {
        "local_name": "Seychelles",
        "languages": [
            "en-SC",
            "fr-SC"
        ],
        "population": 96762,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea",
        "uppercase_fields": [
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "SD": {
        "local_name": "as-Sūdān / السودان",
        "languages": [
            "ar-SD",
            "en",
            "fia"
        ],
        "population": 41801533,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "locality_type": "district",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "SE": {
        "local_name": "Sverige",
        "languages": [
            "sv-SE",
            "se",
            "sma",
            "fi-SE"
        ],
        "population": 10183175,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "locality_type": "post_town",
        "postal_code_prefix": "SE-",
        "postcode_regex": "\\d{3} ?\\d{2}",
        "postcode_format": "### ##"
    },
    "SG": {
        "local_name": "Singapura",
        "languages": [
            "cmn",
            "en-SG",
            "ms-SG",
            "ta-SG",
            "zh-SG"
        ],
        "population": 5638676,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "postalCode"
        ],
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "SH": {
        "local_name": "Saint Helena",
        "languages": [
            "en-SH"
        ],
        "population": 7460,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "(?:ASCN|STHL) 1ZZ",
        "postcode_format": "STHL 1ZZ"
    },
    "SI": {
        "local_name": "Slovenija",
        "languages": [
            "sl",
            "sh"
        ],
        "population": 2067372,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postal_code_prefix": "SI-",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "SJ": {
        "local_name": "Svalbard og Jan Mayen",
        "languages": [
            "no",
            "ru"
        ],
        "population": 2550,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "locality_type": "post_town",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "SK": {
        "local_name": "Slovensko",
        "languages": [
            "sk",
            "hu"
        ],
        "population": 5447011,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "postcode_regex": "\\d{3} ?\\d{2}",
        "postcode_format": "### ##"
    },
    "SL": {
        "local_name": "Sierra Leone",
        "languages": [
            "en-SL",
            "men",
            "tem"
        ],
        "population": 7650154,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "SM": {
        "local_name": "San Marino",
        "languages": [
            "it-SM"
        ],
        "population": 33785,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "required_fields": [
            "addressLine1",
            "postalCode"
        ],
        "postcode_regex": "4789\\d",
        "postcode_format": "4789#"
    },
    "SN": {
        "local_name": "Sénégal",
        "languages": [
            "fr-SN",
            "wo",
            "fuc",
            "mnk"
        ],
        "population": 15854360,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "SO": {
        "local_name": "Soomaaliya – aṣ-Ṣūmāl / الصومال‎",
        "languages": [
            "so-SO",
            "ar-SO",
            "it",
            "en-SO"
        ],
        "population": 15008154,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "[A-Z]{2} ?\\d{5}",
        "postcode_format": "@@  #####"
    },
    "SR": {
        "local_name": "Suriname",
        "languages": [
            "nl-SR",
            "en",
            "srn",
            "hns",
            "jv"
        ],
        "population": 575991,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea",
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "administrativeArea"
        ],
        "administrative_area_type": "district",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "SS": {
        "local_name": "Sudan Kusini",
        "languages": [
            "en"
        ],
        "population": 8260490,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "ST": {
        "local_name": "São Tomé e Príncipe",
        "languages": [
            "pt-ST"
        ],
        "population": 197700,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "SV": {
        "local_name": "El Salvador",
        "languages": [
            "es-SV"
        ],
        "population": 6420744,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode-%locality\\n%administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "CP [1-3][1-7][0-2]\\d",
        "postcode_format": "CP ####"
    },
    "SX": {
        "population": 40654,
        "languages": [
            "nl",
            "en"
        ],
        "postcode_regex": "",
        "postcode_format": ""
    },
    "SY": {
        "local_name": "Sūriyā / سوريا",
        "languages": [
            "ar-SY",
            "ku",
            "hy",
            "arc",
            "fr",
            "en"
        ],
        "population": 16906283,
        "administrative_area_type": "governorate",
        "locality_type": "district",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "SZ": {
        "local_name": "Swaziland",
        "languages": [
            "en-SZ",
            "ss-SZ"
        ],
        "population": 1136191,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "postalCode"
        ],
        "postcode_regex": "[HLMS]\\d{3}",
        "postcode_format": "@###"
    },
    "TC": {
        "local_name": "Turks and Caicos Islands",
        "languages": [
            "en-TC"
        ],
        "population": 37665,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "postalCode"
        ],
        "postcode_regex": "TKCA 1ZZ",
        "postcode_format": "TKCA 1ZZ"
    },
    "TD": {
        "local_name": "Tchad – Tishād / تشاد",
        "languages": [
            "fr-TD",
            "ar-TD",
            "sre"
        ],
        "population": 15477751,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "TF": {
        "local_name": "Terres australes et antarctiques françaises",
        "languages": [
            "fr"
        ],
        "population": 140,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "TG": {
        "local_name": "Togo",
        "languages": [
            "fr-TG",
            "ee",
            "hna",
            "kbp",
            "dag",
            "ha"
        ],
        "population": 7889094,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "TH": {
        "local_name": "Tyland / ประเทศไทย",
        "languages": [
            "th",
            "en"
        ],
        "population": 69428524,
        "locale": "th",
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality, %locality\\n%administrativeArea %postalCode",
        "local_format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality %locality\\n%administrativeArea %postalCode",
        "uppercase_fields": [
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "TJ": {
        "local_name": "Tadzhikistan / Тоҷикистон",
        "languages": [
            "tg",
            "ru"
        ],
        "toponym_locale": "phon",
        "population": 9100837,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "TK": {
        "local_name": "Tokelau",
        "languages": [
            "tkl",
            "en-TK"
        ],
        "population": 1466,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "TL": {
        "local_name": "Timor-Leste – Timor Lorosa'e",
        "languages": [
            "tet",
            "pt-TL",
            "id",
            "en"
        ],
        "population": 1267972,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "TM": {
        "local_name": "Türkmenistan",
        "languages": [
            "tk",
            "ru",
            "uz"
        ],
        "population": 5850908,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "TN": {
        "local_name": "Tūnis / تونس‎",
        "languages": [
            "ar-TN",
            "fr"
        ],
        "population": 11565204,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_type": "governorate",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "TO": {
        "local_name": "Tonga",
        "languages": [
            "to",
            "en-TO"
        ],
        "population": 103197,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "TR": {
        "local_name": "Türkiye",
        "languages": [
            "tr-TR",
            "ku",
            "diq",
            "az",
            "av"
        ],
        "population": 82319724,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality/%administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "locality_type": "district",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "TT": {
        "local_name": "Trinidad and Tobago",
        "languages": [
            "en-TT",
            "hns",
            "fr",
            "es",
            "zh"
        ],
        "population": 1389858,
        "administrative_area_code": "ADM1",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "TV": {
        "local_name": "Tuvalu",
        "languages": [
            "tvl",
            "en",
            "sm",
            "gil"
        ],
        "population": 11508,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea",
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "TW": {
        "local_name": "Táiwān / 台湾",
        "languages": [
            "zh-TW",
            "zh",
            "nan",
            "hak"
        ],
        "population": 22894384,
        "locale": "zh-Hant",
        "format": "%familyName %givenName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea %postalCode",
        "local_format": "%postalCode\\n%administrativeArea%locality\\n%addressLine1\\n%addressLine2\\n%organization\\n%familyName %givenName",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "administrative_area_type": "county",
        "administrative_area_code": "ADM2",
        "subdivision_depth": 2,
        "postcode_regex": "\\d{3}(?:\\d{2,3})?",
        "postcode_format": "#####"
    },
    "TZ": {
        "local_name": "Tanzania",
        "languages": [
            "sw-TZ",
            "en",
            "ar"
        ],
        "population": 56318348,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4,5}",
        "postcode_format": "####|#####"
    },
    "UA": {
        "local_name": "Ukrayina / Україна",
        "languages": [
            "uk",
            "ru-UA",
            "rom",
            "pl",
            "hu"
        ],
        "population": 44622516,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_type": "oblast",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "UG": {
        "local_name": "Uganda",
        "languages": [
            "en-UG",
            "lg",
            "sw",
            "ar"
        ],
        "population": 42723139,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "UM": {
        "local_name": "United States Minor Outlying Islands",
        "languages": [
            "en-UM"
        ],
        "population": 0,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "postal_code_type": "zip",
        "postcode_regex": "96898",
        "postcode_format": "96898"
    },
    "US": {
        "local_name": "United States of America",
        "languages": [
            "en-US",
            "es-US",
            "haw",
            "fr"
        ],
        "population": 327167434,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality, %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postal_code_type": "zip",
        "postcode_regex": "(\\d{5})(?:[ \\-](\\d{4}))?",
        "postcode_format": "#####-####"
    },
    "UY": {
        "local_name": "Uruguay",
        "languages": [
            "es-UY"
        ],
        "population": 3449299,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %administrativeArea",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "UZ": {
        "local_name": "Oʻzbekiston",
        "languages": [
            "uz",
            "ru",
            "tg"
        ],
        "region_language": {
            "QR": "kaa"
        },
        "toponym_locale": "uz",
        "population": 32955400,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality\\n%administrativeArea",
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{6}",
        "postcode_format": "######"
    },
    "VA": {
        "local_name": "Civitas Vaticana – Città del Vaticano",
        "languages": [
            "la",
            "it",
            "fr"
        ],
        "population": 921,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "00120",
        "postcode_format": "00120"
    },
    "VC": {
        "local_name": "Saint Vincent and the Grenadines",
        "languages": [
            "en-VC",
            "fr"
        ],
        "population": 110211,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode",
        "postcode_regex": "VC\\d{4}",
        "postcode_format": "VC####"
    },
    "VE": {
        "local_name": "Venezuela",
        "languages": [
            "es-VE"
        ],
        "population": 28870195,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %postalCode, %administrativeArea",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea"
        ],
        "uppercase_fields": [
            "locality",
            "administrativeArea"
        ],
        "administrative_area_type": "state",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "VG": {
        "local_name": "British Virgin Islands",
        "languages": [
            "en-VG"
        ],
        "population": 29802,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1"
        ],
        "postcode_regex": "VG\\d{4}",
        "postcode_format": "VG####"
    },
    "VI": {
        "local_name": "United States Virgin Islands",
        "languages": [
            "en-VI"
        ],
        "population": 106977,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality %administrativeArea %postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "administrativeArea",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "familyName",
            "additionalName",
            "givenName",
            "organization",
            "administrativeArea"
        ],
        "administrative_area_type": "island",
        "administrative_area_code": "ADM1",
        "postal_code_type": "zip",
        "postcode_regex": "(008(?:(?:[0-4]\\d)|(?:5[01])))(?:[ \\-](\\d{4}))?",
        "postcode_format": "#####-####"
    },
    "VN": {
        "local_name": "Việt Nam",
        "languages": [
            "vi",
            "en",
            "fr",
            "zh",
            "km"
        ],
        "population": 95540395,
        "format": "%familyName %givenName\\n%organization\\n%addressLine1\\n%addressLine2\\n%locality\\n%administrativeArea %postalCode",
        "administrative_area_code": "ADM1",
        "subdivision_depth": 1,
        "postcode_regex": "\\d{5}\\d?",
        "postcode_format": "######"
    },
    "VU": {
        "local_name": "Vanuatu",
        "languages": [
            "bi",
            "en-VU",
            "fr-VU"
        ],
        "population": 292680,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "WF": {
        "local_name": "Wallis-et-Futuna",
        "languages": [
            "wls",
            "fud",
            "fr-WF"
        ],
        "population": 16025,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "986\\d{2}",
        "postcode_format": "#####"
    },
    "WS": {
        "local_name": "Sāmoa",
        "languages": [
            "sm",
            "en-WS"
        ],
        "population": 196130,
        "postcode_regex": "",
        "postcode_format": ""
    },
    "YE": {
        "local_name": "al-Yaman / ٱلْيَمَن‎",
        "languages": [
            "ar-YE"
        ],
        "population": 28498687,
        "administrative_area_type": "governorate",
        "postcode_regex": "",
        "postcode_format": ""
    },
    "YT": {
        "local_name": "Mayotte",
        "languages": [
            "fr-YT"
        ],
        "population": 159042,
        "format": "%organization\\n%givenName %familyName\\n%addressLine1\\n%addressLine2\\n%postalCode %locality %sortingCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "uppercase_fields": [
            "addressLine1",
            "addressLine2",
            "locality",
            "sortingCode"
        ],
        "postcode_regex": "976\\d{2}",
        "postcode_format": "#####"
    },
    "ZA": {
        "local_name": "iNingizimu Afrika – uMzantsi Afrika – Suid-Afrika",
        "languages": [
            "zu",
            "xh",
            "af",
            "nso",
            "en-ZA",
            "tn",
            "st",
            "ts",
            "ss",
            "ve",
            "nr"
        ],
        "population": 57779622,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%dependentLocality\\n%locality\\n%postalCode",
        "required_fields": [
            "addressLine1",
            "locality",
            "postalCode"
        ],
        "administrative_area_code": "ADM1",
        "postcode_regex": "\\d{4}",
        "postcode_format": "####"
    },
    "ZM": {
        "local_name": "Zambia",
        "languages": [
            "en-ZM",
            "bem",
            "loz",
            "lun",
            "lue",
            "ny",
            "toi"
        ],
        "population": 17351822,
        "format": "%givenName %familyName\\n%organization\\n%addressLine1\\n%addressLine2\\n%postalCode %locality",
        "postcode_regex": "\\d{5}",
        "postcode_format": "#####"
    },
    "ZW": {
        "local_name": "Zimbabwe",
        "languages": [
            "en-ZW",
            "sn",
            "nr",
            "nd"
        ],
        "population": 14439018,
        "postcode_regex": "",
        "postcode_format": ""
    }
}


SUBREGION_TYPES = {
    # Hong Kong
    'area': pgettext_lazy("administrative area type", "area"),
    # United Kingdom
    'country': pgettext_lazy("administrative area type", "country"),
    'county': pgettext_lazy("administrative area type", "county"),
    'department': pgettext_lazy("administrative area type", "department"),
    'district': pgettext_lazy("administrative area type", "district"),
    # South Korea
    'do_si': pgettext_lazy("administrative area type", "province / city"),
    # United Arab Emirates
    'emirate': pgettext_lazy("administrative area type", "emirate"),
    # Bosnia and Herzegovina
    'entity': pgettext_lazy("administrative area type", "entity"),
    # Austria, Germany
    'federal state': pgettext_lazy("administrative area type", "federal state"),
    # Russia
    'federal subject': pgettext_lazy("administrative area type", "federal subject"),
    'governorate': pgettext_lazy("administrative area type", "governorate"),
    'island': pgettext_lazy("administrative area type", "island"),
    # Belorus, Bulgaria, Kazakhstan, Kyrgyzstan, Ukraine
    'oblast': pgettext_lazy("administrative area type", "oblast"),
    'parish': pgettext_lazy("administrative area type", "parish"),
    # Japan
    'prefecture': pgettext_lazy("administrative area type", "prefecture"),
    'region': pgettext_lazy("administrative area type", "region"),
    'state': pgettext_lazy("administrative area type", "state"),
    # Poland
    'voivodeship': pgettext_lazy("administrative area type", "voivodeship"),
}


def countries_with_mandatory_region():
    if not hasattr(countries_with_mandatory_region, '_result_cache'):
        countries_with_mandatory_region._result_cache = frozenset(
            country_code for (country_code, data) in COUNTRIES_DATA.items()
            if 'administrativeArea' in data.get('required_fields', [])
        )
    return countries_with_mandatory_region._result_cache
