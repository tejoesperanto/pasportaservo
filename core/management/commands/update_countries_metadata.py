import csv
import json
import re
import sys
from collections import OrderedDict

from django.core.management.base import BaseCommand

import requests

from hosting.countries import COUNTRIES_DATA

COUNTRIES_METADATA_FILE = 'hosting/countries.py'
GEONAMES_SOURCE_URL = 'http://download.geonames.org/export/dump/countryInfo.txt'
COMMERCEGUYS_SOURCE_URL = (
    'https://raw.githubusercontent.com/commerceguys/addressing'
    '/master/src/AddressFormat/AddressFormatRepository.php'
)


class Command(BaseCommand):
    help = """
        Updates the meta-data (population, post code formats) for the
        countries of the world.
        """

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']

        # Read existing local database file.
        with open(COUNTRIES_METADATA_FILE, 'r') as source_file:
            file_old_contents = source_file.read()
        bits = re.match(
            '(.*\nCOUNTRIES_DATA = )(?:\{\n.*?\n\})(.*)', file_old_contents, re.DOTALL).groups()

        # Update countries dict with the new metadata obtained from CommerceGuys and GeoNames.
        country_list = OrderedDict(COUNTRIES_DATA)
        try:
            csv_data = requests.get(GEONAMES_SOURCE_URL)
            assert csv_data.status_code == 200, ('CSV', csv_data)
            json_data = requests.get(COMMERCEGUYS_SOURCE_URL)
            assert json_data.status_code == 200, ('JSON', json_data)
        except requests.exceptions.ConnectionError as e:
            if self.verbosity >= 1:
                self.stdout.write(self.style.ERROR(
                    f"** Metadata update failed. {e.args[0].reason}."
                ))
            sys.exit(1)
        except AssertionError as err:
            if self.verbosity >= 1:
                self.stdout.write(self.style.ERROR(
                    f"** Metadata update failed. {err.args[0][0]} source data cannot be accessed "
                    f"(HTTP {getattr(err.args[0][1], 'status_code')})."
                ))
            sys.exit(1)
        else:
            # Load the CSV data into a Python array of dictionaries.
            csv_data = csv.DictReader(
                filter(
                    lambda line: not line.startswith("# ") and not line.startswith("#\t"),
                    csv_data.text.splitlines()),
                delimiter='\t')
            # Find the PHP array with the definitions of the postal formats.
            json_data = re.search(r'\$definitions = \[(.+),\s+\];', json_data.text, re.DOTALL).group(1)
            # Convert each PHP array entry into a valid JSON object.
            json_data, how_many = re.subn(
                r'^( +)(\'[A-Z]{2}\') => \[(.+?),\n\1\]', r'\1\2 : {\3\1}',
                json_data,
                flags=re.DOTALL + re.MULTILINE)
            # Make sure internal arrays do not contain a comma after the last element.
            json_data = re.sub(r'\[\n\s+(.+?),\n\s+\]', r'[ \1 ]', json_data)
            # Ensure a valid JSON syntax: double the backslashes, put all strings in double
            # quotes, and separate object names from object values by colons.
            json_data = json_data.replace('\\', '\\\\').replace("'", '"').replace('=>', ':')
            # Finally load as JSON data into a Python dictionary.
            json_data = json.loads(f'{{ {json_data} }}')
        replacement_format = {
            'AI': "AI-2640",
            'CX': "",  # Infer from regex.
            'EC': "",  # Infer from regex.
            'GG': "GY# #@@|GY## #@@",
            'HN': "",  # Infer from regex.
            'IM': "IM# #@@|IM## #@@",
            'JE': "JE# #@@|JE## #@@",
            'MU': "#####|###@@###",
            'NF': "",  # Infer from regex.
            'NI': "",  # Infer from regex.
            'PE': "0####|1####|2####",
            'PW': "96939|96939-####|96940|96940-####",
            'TZ': "####|#####",
            'VA': "",  # Infer from regex.
        }

        for i, country in [(i, k) for i, k in enumerate(csv_data, start=1) if k['#ISO'] in COUNTRIES_DATA]:
            code = country['#ISO']
            country_list[code]['population'] = int(country['Population'])
            if country['Languages']:
                country_list[code]['languages'] = country['Languages'].rstrip(',').split(',')
            postcode_pattern = False
            if code in json_data:
                postcode_pattern = json_data[code].pop('postal_code_pattern', "")
                country_list[code].update(json_data[code])
                country_list[code]['postcode_regex'] = postcode_pattern
            if not country_list[code].get('postcode_regex'):
                country_list[code]['postcode_regex'] = country['Postal Code Regex'].lstrip('^').rstrip('$')
            country_list[code]['postcode_format'] = country['Postal Code Format']
            if code in replacement_format:
                # For these countries, the format provided by GeoNames is incorrect or missing.
                country_list[code]['postcode_format'] = replacement_format[code]
            if not country_list[code]['postcode_format'] and country_list[code]['postcode_regex']:
                # In case the format is not provided by GeoNames, attempt to convert
                # the (simple) regex into the #@ format representation.
                converted_regex = re.sub(
                    r'(\\[d])(?:\{(\d)\})?',
                    lambda m: "#" * (int(m.group(2)) if m.group(2) else 1),
                    country_list[code]['postcode_regex'])
                if re.match(r'^[A-Z0-9# -]+$', converted_regex):
                    country_list[code]['postcode_format'] = converted_regex

            if self.verbosity >= 2:
                self.stdout.write(
                    f"{i:3d}. {country['#ISO']} ({country['Country']:^24})"
                    f"\t{country['Population']:<10}\t{country_list[code]['postcode_format']}"
                )
                if not postcode_pattern and country['Postal Code Regex']:
                    self.stdout.write(f"\tpostcode regex from geonames: {country['Postal Code Regex']}")

        if self.verbosity >= 1:
            self.stdout.write(
                "COUNTRIES WITH NO POSTCODE FORMAT:\n{}".format([
                    code for code in country_list
                    if country_list[code]['postcode_regex']
                    and not country_list[code]['postcode_format']
                ])
            )

        # Generate new local database file.
        file_new_contents = bits[0]
        file_new_contents += json.dumps(country_list, indent=4, ensure_ascii=False).replace('null', str(None))
        file_new_contents += bits[1]
        with open(COUNTRIES_METADATA_FILE, 'w', encoding='utf-8') as output_file:
            output_file.write(file_new_contents)

        # Print command execution summary.
        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(
                "** Metadata update successfully completed."
            ))
