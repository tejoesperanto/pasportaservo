# This command updates the data regarding administrative subdivisions of the
# requested countries, including their Esperanto names and bounding boxes.
#
# We collect all administrative subdivision data from the 'Addressing' library
# of CommerceGuys, and the subdivisions for countries for which the library
# says the administrative area is an obligatory part of the address or which
# are defined as either 'federal state' or 'regional state' by Wikipedia:
# https://en.wikipedia.org/wiki/List_of_administrative_divisions_by_country.
#
# The exceptions are:
#   Nepal -  the provinces of Nepal are "work in progress" and are not yet
#            fully established.
#   Serbia - GeoNames does not include Kosovo districts when querying for RS;
#            however, we don't have Kosovo as a separate country.
#   South Sudan -
#            due to low quality of the data provided by GeoNames.
#   Sudan -  the data in GeoNames first needs to be updated and organised to
#            be suitable for algorithmic processing.

import json
import re

from django.contrib.gis.geos import LineString, Point
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.termcolors import make_style

import requests
from django_countries.data import COUNTRIES
from unidecode import unidecode

from hosting.countries import COUNTRIES_DATA
from hosting.models import CountryRegion, LocationType, Whereabouts
from maps import SRID

GEONAMES_SOURCE_URL = (
    'http://api.geonames.org/searchJSON?country={country}&featureCode={code}'
    '&style=FULL&lang=eo&maxRows=1000&username=pasportaservo'
)
GEONAMES_DETAILS_SOURCE_URL = (
    'http://api.geonames.org/getJSON?geonameId={}&username=pasportaservo'
)
COMMERCEGUYS_SOURCE_URL = (
    'https://raw.githubusercontent.com/commerceguys/addressing'
    '/master/resources/subdivision/{}.json'
)


class Command(BaseCommand):
    help = """
        Updates the administrative units (e.g., states or provinces) for a country.
        """

    def add_arguments(self, parser):
        """
        The command can be given a list of ISO country codes to update,
        as an argument. A missing argument or the word "ALL" mean that
        all countries in the local database will be refreshed.
        """
        parser.add_argument(
            'update_countries',
            nargs='*', choices=tuple(sorted(COUNTRIES.keys())) + ('ALL',), default='ALL',
            metavar='country code',
            help="one or more country codes to update, omit to update all countries.")
        parser.add_argument(
            '-s', '--start-from',
            default='AA', choices='ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            help="when all countries are being updated, begin with the ISO code "
                 "starting with this letter.")
        parser.add_argument(
            '-e', '--end-before',
            default='ZZ', choices='ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            help="when all countries are being updated, stop before the ISO code "
                 "starting with this letter.")

    TOPONYM_REPLACEMENTS = {
        "EG": "Governorate",
        "IR": "Province",
        "MP": "Municipality",
        "NR": "District",
        "TW": "County",
        "VN": ["Province", "City"],
    }

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.requested_countries = update_countries = options['update_countries']
        if not update_countries or 'ALL' in update_countries:
            update_countries = (
                c for c in sorted(COUNTRIES.keys())
                if c >= options['start_from'] and c < options['end_before']
            )
            self.requested_countries = list(sorted(COUNTRIES.keys()))
            self.full_update = True
        else:
            self.full_update = False

        country_result, country_removals = {}, {}
        for country_code in update_countries:
            # First try to retrieve the high-quality data from CommerceGuys.
            result, json_data = self.load_commerceguys_data(country_code)
            if not result:
                country_result[country_code] = (False, False)
                continue
            if self.verbosity >= 2:
                self.stdout.write(self.country_output_line(country_code), ending="")

            # When we have json data, use it as the main source.
            if country_code == 'IR':
                # Temporary solution until Google & CommerceGuys update their dataset.
                json_data = None
            if json_data:
                region_names = self.process_commerceguys_data(country_code, json_data)
                if self.removed_regions:
                    country_removals[country_code] = self.removed_regions
                self.print_country_summary(country_code, region_names, source="ComGuys")

            # Retrieve country data from GeoNames.
            result, geonames_data = self.load_geonames_data(country_code, json_data is not None)
            if not result:
                country_result[country_code] = (json_data is not None, result)
                self.update_esperanto_name_manually(country_code)
                continue

            # When we don't have json data, use GeoNames as the source (with caution).
            if json_data is None:
                region_names = self.process_geonames_data(country_code, geonames_data)
                if self.removed_regions:
                    country_removals[country_code] = self.removed_regions
                self.print_country_summary(country_code, region_names, source="GeoNAPI")

            # Update Esperanto names and geodata for all regions.
            self.update_esperanto_name_and_bbox(country_code, json_data, geonames_data)

            if self.verbosity >= 2:
                self.stdout.write("\n")
            country_result[country_code] = (True, True)

        # Print command execution summary.
        self.print_overall_summary(
            country_result, (True, True), self.style.SUCCESS,
            "** Update successfully completed")
        self.print_overall_summary(
            country_result, (False, None), make_style(fg='green'),
            "** Update skipped")
        self.print_overall_summary(
            country_result, (True, False), self.style.WARNING,
            "** Update partially done (no GeoNames data)")
        self.print_overall_summary(
            country_result, (False, False), self.style.ERROR,
            "** Update failed")
        if any(country_removals.values()):
            if self.verbosity >= 1:
                self.stdout.write(
                    make_style(fg='red')(
                        "** Some regions of {} were removed!"
                        .format(", ".join(country_removals.keys()))
                    ), ending=" "
                )
                self.stdout.write(
                    "Run the {} command to review the invalidated "
                    "addresses in the database."
                    .format(make_style(opts=('underscore',))("check_country_regions"))
                )
            if self.verbosity == 2:
                self.stdout.write(make_style(fg='red')(
                    json.dumps(country_removals, indent=3, ensure_ascii=False)
                ))

    def country_output_line(self, country_code):
        i = self.requested_countries.index(country_code) + 1
        return f"{i:3d}. {country_code} ({COUNTRIES[country_code]}) "

    def get_country_regions_queryset(self, country_code):
        return (
            CountryRegion.objects.filter(country=country_code)
            .values('iso_code', 'latin_code', 'latin_name')
        )

    def get_country_toponym_replacement_regex(self, country_code):
        if country_code in self.TOPONYM_REPLACEMENTS:
            prefixes = self.TOPONYM_REPLACEMENTS[country_code]
            prefixes = prefixes if isinstance(prefixes, list) else [prefixes]
            return re.compile(fr'\s({"|".join(prefixes)})$')
        else:
            return None

    def pre_process(self, country_code):
        self.old_regions = {
            r['iso_code']: r
            for r in self.get_country_regions_queryset(country_code).all()
        }

    def normalize_toponym(self, toponym_name, trim_re):
        if trim_re:
            toponym_name = trim_re.sub("", toponym_name)
        return toponym_name.replace(" and ", " & ")

    def post_process(self, country_code, all_iso_codes):
        CountryRegion.objects.filter(
            Q(country=country_code) & ~Q(iso_code__in=all_iso_codes)
        ).delete()
        self.new_regions = {
            r['iso_code']: r
            for r in self.get_country_regions_queryset(country_code).all()
        }
        self.removed_regions = [
            r for c, r in self.old_regions.items()
            if c in self.old_regions.keys() - self.new_regions.keys()
        ]

    def load_commerceguys_data(self, country_code):
        try:
            json_data = requests.get(COMMERCEGUYS_SOURCE_URL.format(country_code))
            assert json_data.status_code in (200, 404)
        except requests.exceptions.ConnectionError as e:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(
                    self.country_output_line(country_code) + f"{e.args[0].reason}."
                ))
            return (False, None)
        except AssertionError:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(
                    self.country_output_line(country_code)
                    + f"JSON source data cannot be accessed (HTTP {json_data.status_code})."
                ))
            return (False, None)
        else:
            try:
                json_data = json.loads(json_data.text) if json_data.status_code == 200 else None
            except Exception as e:
                if self.verbosity >= 2:
                    self.stdout.write(self.style.ERROR(
                        self.country_output_line(country_code) + f"{e}."
                    ))
                return (False, None)
        return (True, json_data)

    def process_commerceguys_data(self, country_code, json_data):
        self.pre_process(country_code)
        iso_codes = []
        toponym_trim_re = self.get_country_toponym_replacement_regex(country_code)

        for i, (region_key, region) in enumerate(json_data['subdivisions'].items(), start=1):
            if not region:
                region = {}
            if 'iso_code' not in region and country_code in ('US', 'RU'):
                continue
            region_iso_code = region.get('iso_code', f"{country_code}-X-{i:02}")[3:]
            region_key = self.normalize_toponym(region_key, toponym_trim_re)
            CountryRegion.objects.update_or_create(
                country=country_code, iso_code=region_iso_code,
                defaults=dict(
                    latin_code=region_key,
                    latin_name=region.get('name', ''),
                    local_code=region.get('local_code', ''),
                    local_name=region.get('local_name', ''),
                )
            )
            iso_codes.append(region_iso_code)

        self.post_process(country_code, iso_codes)
        return json_data['subdivisions'].keys()

    def load_geonames_data(self, country_code, has_json, details=False, geonameid=None):
        if 'administrative_area_code' not in COUNTRIES_DATA[country_code]:
            if self.verbosity >= 2:
                if has_json or not self.full_update:
                    self.stdout.write(make_style(opts=['bold'])(
                        ("\n" if not has_json else "")
                        + "\t** GEONAMES data cannot be retrieved, admin area code is missing!"
                    ))
                    return (False, None)
                else:
                    self.stdout.write("\n")
                    return (None, None)

        geonames_data = None
        try:
            if not details:
                source_url = GEONAMES_SOURCE_URL.format(
                    country=country_code,
                    code=COUNTRIES_DATA[country_code]['administrative_area_code'])
            else:
                assert geonameid is not None
                source_url = GEONAMES_DETAILS_SOURCE_URL.format(geonameid)
            geonames_data = requests.get(source_url)
            assert geonames_data.status_code == 200
        except (Exception, AssertionError):
            if self.verbosity >= 2:
                for_feature = f" (for {geonameid})" if details else ""
                self.stdout.write(self.style.ERROR(
                    f"\n\t** GEONAMES source data{for_feature} cannot be accessed "
                    f"(HTTP {getattr(geonames_data, 'status_code', '---')})."
                ))
            return (False, None)
        else:
            try:
                geonames_data = json.loads(geonames_data.text)
            except Exception as e:
                if self.verbosity >= 2:
                    for_feature = f" (for {geonameid})" if details else ""
                    self.stdout.write(self.style.ERROR(
                        f"\n\t** GEONAMES source data{for_feature} is invalid; {e}."
                    ))
                return (False, None)

        return (True, geonames_data)

    def process_geonames_data(self, country_code, geonames_data):
        code_key = {
            'ADM1': 'adminCodes1', 'ADM2': 'adminCodes2'
        }[COUNTRIES_DATA[country_code]['administrative_area_code']]
        local_country_lang = COUNTRIES_DATA[country_code]['languages'][0].split('-')[0]

        self.pre_process(country_code)
        iso_codes = []
        region_names = []
        try:
            regions = geonames_data['geonames']
        except KeyError:
            raise Exception(
                geonames_data.get('status', {}).get('message', "")
                or f"GeoNames did not provide expected data: {geonames_data}"
            ) from None
        toponym_trim_re = self.get_country_toponym_replacement_regex(country_code)

        for i in range(len(regions)):
            if code_key not in regions[i] or 'ISO3166_2' not in regions[i][code_key]:
                continue
            load_result, region = self.load_geonames_data(
                country_code, False, details=True, geonameid=regions[i]['geonameId'])
            if load_result:
                regions[i] = region
                regions[i]['_complete'] = True
            else:
                region = regions[i]

            region_iso_code = region[code_key]['ISO3166_2']
            update_fields = dict(
                latin_code=self.normalize_toponym(region['toponymName'], toponym_trim_re),
            )
            if '_complete' in region:
                # Find the name of the region in the local language. Use the regional
                # language if defined, else the most-spoken language of the country.
                local_lang = (
                    COUNTRIES_DATA[country_code].get('region_language', {})
                    .get(region_iso_code, local_country_lang)
                    .split('-')[0]
                )
                local_name = self.get_localised_name(region, local_lang)
                update_fields.update(dict(local_code=local_name['name']))
                # For some countries, it is better to use a local version of the name,
                # instead of the toponym name offered by GeoNames.
                if 'toponym_locale' in COUNTRIES_DATA[country_code]:
                    if COUNTRIES_DATA[country_code]['toponym_locale'] != 'DECODE':
                        latin_name = self.get_localised_name(
                            region, COUNTRIES_DATA[country_code]['toponym_locale'])
                        latin_name['name'] = latin_name['name'].replace(" and ", " & ")
                    else:
                        latin_name = {'name': unidecode(local_name['name'])}
                    if latin_name['name']:
                        update_fields['latin_code'] = latin_name['name']
            CountryRegion.objects.update_or_create(
                country=country_code, iso_code=region_iso_code,
                defaults=update_fields
            )
            iso_codes.append(region_iso_code)
            region_names.append(update_fields['latin_code'])

        self.post_process(country_code, iso_codes)
        return region_names

    def get_localised_name(self, region_data, for_lang):
        alternate_names = list(filter(
            lambda name: name.get('lang') == for_lang and 'isHistoric' not in name,
            region_data.get('alternateNames', [])
        ))
        try:
            localised_name = next(filter(
                lambda name: 'isPreferredName' in name,
                alternate_names
            ))
        except StopIteration:
            localised_name = alternate_names[0] if alternate_names else {'name': ""}
        return localised_name

    def update_esperanto_name_and_bbox(self, country_code, json_data, geonames_data):
        all_iso_codes = (
            CountryRegion.objects.filter(country=country_code)
            .values_list('iso_code', 'latin_code', 'latin_name', 'esperanto_name')
        )
        code_key = {
            'ADM1': 'adminCodes1', 'ADM2': 'adminCodes2'
        }[COUNTRIES_DATA[country_code]['administrative_area_code']]

        updated_eonames = {}
        for region_code, latin_code, latin_name, existing_eoname in all_iso_codes:
            try:
                region = next(filter(
                    lambda r: r[code_key]['ISO3166_2'] == region_code,
                    geonames_data['geonames']))
            except (StopIteration, KeyError):
                continue
            if '_complete' not in region:
                load_result, region = self.load_geonames_data(
                    country_code, json_data is not None,
                    details=True, geonameid=region['geonameId'])
                if not load_result:
                    continue

            # Update the geographical data for the region.
            if 'bbox' in region:
                Whereabouts.objects.update_or_create(
                    type=LocationType.REGION,
                    state=region_code,
                    country=country_code,
                    defaults=dict(
                        name=(latin_name or latin_code).upper(),
                        bbox=LineString(
                            (region['bbox']['west'], region['bbox']['south']),
                            (region['bbox']['east'], region['bbox']['north']),
                            srid=SRID,
                        ),
                        center=Point(float(region['lng']), float(region['lat']), srid=SRID),
                    )
                )
            # Update the Esperanto name for the region.
            region_eoname = self.get_localised_name(region, 'eo')['name']
            if not region_eoname:
                continue
            if region_eoname != existing_eoname:
                (
                    CountryRegion.objects
                    .filter(country=country_code, iso_code=region_code)
                    .update(esperanto_name=region_eoname)
                )
                updated_eonames[region_code] = f"{existing_eoname or '.'}->{region_eoname}"

        self.print_esperanto_update_summary(updated_eonames, json_data == {})

    def update_esperanto_name_manually(self, country_code):
        eonames = {
            'HK': {
                'X-01': "Kaŭluna Duoninsulo",
                'X-02': "Honkonga Insulo",
                'X-03': "Novaj Teritorioj",
            },
            'KY': {
                'X-01': "Brak-Kajmano",
                'X-02': "Granda Kajmano",
                'X-03': "Malgranda Kajmano",
            },
        }
        if country_code not in eonames:
            return

        all_iso_codes = (
            CountryRegion.objects.filter(country=country_code)
            .values_list('iso_code', 'esperanto_name')
        )
        updated_eonames = {}
        for region_code, existing_eoname in all_iso_codes:
            region_eoname = eonames[country_code].get(region_code)
            if not region_eoname:
                continue
            if region_eoname != existing_eoname:
                (
                    CountryRegion.objects
                    .filter(country=country_code, iso_code=region_code)
                    .update(esperanto_name=region_eoname)
                )
                updated_eonames[region_code] = f"{existing_eoname or '.'}->{region_eoname}"

        self.print_esperanto_update_summary(updated_eonames, False)

    def print_esperanto_update_summary(self, updated_eonames, linebreak):
        if self.verbosity >= 3:
            if updated_eonames:
                self.stdout.write(make_style(fg='cyan')(
                    ("\n" if linebreak else "") + "\tUPDATED: {}".format(updated_eonames)
                ))

    def print_country_summary(self, country_code, region_names, source):
        if self.verbosity >= 2:
            self.stdout.write(
                "\t" + str(list(region_names)) + f"   from {source}"
            )
        if self.verbosity >= 3:
            added = (self.new_regions.keys() - self.old_regions.keys())
            if added:
                self.stdout.write(make_style(fg='green')(
                    "\tADDED:   {}".format([
                        tuple(r.values()) for c, r in self.new_regions.items() if c in added
                    ])
                ))
            if self.removed_regions:
                self.stdout.write(make_style(fg='red')(
                    "\tREMOVED: {}".format([
                        tuple(r.values()) for r in self.removed_regions
                    ])
                ))
            changed = [
                tuple(
                    f"{self.old_regions[c][field] or '.'}->{self.new_regions[c][field] or '.'}"
                    if self.old_regions[c][field] != self.new_regions[c][field]
                    else self.old_regions[c][field]
                    for field in self.old_regions[c].keys()
                )
                for c in (self.old_regions.keys() & self.new_regions.keys())
                if any(self.old_regions[c][field] != self.new_regions[c][field]
                       for field in self.old_regions[c].keys())
            ]
            if changed:
                self.stdout.write(make_style(fg='magenta')(
                    "\tCHANGED: {}".format(changed)
                ))

    def print_overall_summary(self, country_result, expected_status, status_style, status_message):
        if self.verbosity >= 1:
            status_countries = sorted(list(filter(
                lambda c: country_result[c] == expected_status,
                country_result)))
            if status_countries:
                if len(status_countries) < 3:
                    listing = "for {}".format(", ".join(status_countries))
                else:
                    listing = "for {} countries: {}".format(
                        len(status_countries), ", ".join(status_countries)
                    )
                self.stdout.write(status_style(status_message + " " + listing))
