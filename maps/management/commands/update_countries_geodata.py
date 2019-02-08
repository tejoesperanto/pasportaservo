"""
This management command generates or updates a local database of boundaries
and center points for the countries defined by the django_countries module.
The countries are geocoded using the OpenCage API, with local modifications
when necessary.

Note: The OpenCage's database is very volatile and there is no guarantee
      that queries which worked in the past will continue to work in the
      future. Upon each update of the local database, it is highly
      recommended to perform a visual verification of the update results.
"""

import json
import re
from collections import OrderedDict

from django.core.management.base import BaseCommand

from django_countries.data import COUNTRIES

from hosting.utils import geocode
from maps.data import COUNTRIES_GEO

COUNTRIES_GEODATA_FILE = 'maps/data.py'


class Command(BaseCommand):
    help = """
        Updates the geo-data (bounding boxes and center points) for the
        countries of the world.
        """

    def add_arguments(self, parser):
        """
        The command can be given a list of ISO country codes to update,
        as an argument. A missing argument or the word "ALL" mean that
        all countries in the local database will be refreshed.
        """
        parser.add_argument(
            'update_countries',
            nargs='*', choices=tuple(COUNTRIES.keys()) + ('ALL',), default='ALL',
            metavar='country code', help="one or more country codes to update, omit to update all countries.")

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        update_countries = options['update_countries']
        if not update_countries or update_countries == 'ALL' or 'ALL' in update_countries:
            update_countries = COUNTRIES.keys()

        # Read existing local database file.
        with open(COUNTRIES_GEODATA_FILE, 'r') as source_file:
            file_old_contents = source_file.read()
        bits = re.match(
            '(.*\nCOUNTRIES_GEO = )(?:\{\n.*?\n\})(.*)', file_old_contents, re.DOTALL).groups()

        # Make countries dict.
        country_list = OrderedDict(COUNTRIES_GEO)
        update_succeeded, update_failed = [], []
        name_replacements = {
            'BQ': "Caribbean Netherlands",
            'CG': "Congo-Brazzaville",
            'CW': "Curaçao island",
            'CX': "Territory of Christmas Island",
            'FR': "Mainland France",
            'FK': "Falkland Islands",
            'KP': "North Korea",
            'KR': "South Korea",
            'MF': "Collectivité de Saint-Martin",
            'MH': "Republic of the Marshall Islands",
            'MT': "Republic of Malta",
            'NL': "Mainland Netherlands",
            'PS': "State of Palestine",
            'VG': "British Virgin Islands",
            'VI': "U.S. Virgin Islands",
            'ZA': "Republic of South Africa",
        }
        code_replacements = {
            'AS': 'US',
            'CC': 'AU',
            'HM': 'AU',
            'PR': 'US',
        }
        autonomous_state_codes = {
            'AW': 'NL',
            'AX': 'FI',
            'BQ': 'NL',
            'CX': 'AU',
            'YT': 'FR',
            'VI': 'VI',
        }
        # SPECIAL CASES:
        # k in ('AQ', 'AW', 'CC', 'CX', 'DJ', 'DM', 'GI', 'GP', 'HM', 'JE', 'MF', 'MO', 'PR', 'SX', 'TF', 'US', 'ZA')
        # TODO Countries which cross the +180/-180 longitude cannot be displayed properly on the map.
        #      Mapbox is working on a solution. Verify that these countries are displayed correctly:
        #      'FJ', 'KI', 'NZ', 'RU'
        for country_code, i in [(k, i) for i, k in enumerate(COUNTRIES.keys(), start=1) if k in update_countries]:
            political_country_code = code_replacements.get(country_code, country_code)
            # For countries which cannot be geocoded normally using the OpenCage's API.
            georesult = custom_calculation(country_code)
            # Otherwise, attempt a strict search.
            if not georesult:
                georesult = geocode(
                    name_replacements.get(country_code, str(COUNTRIES[country_code])),
                    country=autonomous_state_codes.get(country_code, political_country_code),
                    multiple=True)
            pointed_result_index = None
            for j, res in enumerate(georesult):
                if (country_code not in autonomous_state_codes and obj_type(res) == 'country') \
                        or (country_code in autonomous_state_codes and obj_type(res) == 'state'):
                    georesult.set_default_result(j)
                    pointed_result_index = j
                    break
            # When not found, search the world for the name of the country.
            general_result_index = None
            if len(georesult) == 0 or pointed_result_index is None or not georesult.bbox:
                georesult = geocode(str(COUNTRIES[country_code]), multiple=True)
                if len(georesult) and obj_type(georesult) != 'country' and country_code != 'AQ':
                    for j, res in enumerate(georesult):
                        if obj_type(res) in ('country', 'state', 'county', 'island') \
                                and res._components.get('ISO_3166-1_alpha-2') == political_country_code:
                            georesult.set_default_result(j)
                            general_result_index = j
                            if obj_type(res) == 'country':
                                break

            # Output the query and search results on screen.
            if self.verbosity >= 2:
                self.stdout.write("{index:3d}. {code} ({name})\t{result!r}".format(
                    index=i, code=country_code, name=COUNTRIES[country_code], result=georesult))
            if self.verbosity >= 3:
                if country_code in code_replacements or country_code in name_replacements:
                    self.stdout.write("\t{code} ({name})".format(
                        code=political_country_code,
                        name=name_replacements.get(country_code, COUNTRIES[country_code])))
                if obj_type(georesult) == 'country' or \
                        obj_type(georesult) == 'state' and country_code in autonomous_state_codes:
                    style = self.style.HTTP_INFO
                elif obj_type(georesult) in ('state', 'county', 'island'):
                    style = self.style.NOTICE
                else:
                    style = self.style.ERROR
                self.stdout.write(style("\t--  {components}".format(
                    components=georesult._components)))
                if general_result_index is not None:
                    self.stdout.write("\t--  [result {index} out of the returned general list]".format(
                        index=general_result_index + 1))
                self.stdout.write("\t--  {bbox}, center: {center}".format(
                    bbox=georesult.bbox, center=georesult.xy))

            # Store the result in the corresponding success or failure list.
            if not georesult.error and len(georesult):
                geodata = {'bbox': georesult.bbox, 'center': georesult.xy}
                if geodata != country_list.get(country_code, {}):
                    update_succeeded.append(country_code)
                country_list[country_code] = geodata
            else:
                update_failed.append(country_code)

        # Generate new local database file.
        file_new_contents = bits[0]
        file_new_contents += json.dumps(country_list, indent=4).replace('null', str(None))
        file_new_contents += bits[1]
        with open(COUNTRIES_GEODATA_FILE, 'w') as output_file:
            output_file.write(file_new_contents)

        # Print command execution summary.
        if self.verbosity >= 1:
            if not update_failed:
                self.stdout.write(self.style.SUCCESS(
                    "** Geodata update successfully completed. {} countries updated.".format(len(update_succeeded))
                ))
                if update_succeeded and self.verbosity >= 2:
                    self.stdout.write(self.style.SUCCESS(
                        "   {}".format(", ".join(update_succeeded))
                    ))
            else:
                self.stdout.write(self.style.ERROR(
                    "** Geodata update failed. {} countries updated, {} countries failed.".format(
                        len(update_succeeded), len(update_failed)
                    )
                ))
                if self.verbosity >= 2:
                    self.stdout.write(self.style.SUCCESS(
                        "   SUCCESS: {}".format(
                            ", ".join(update_succeeded) if update_succeeded else "none"
                        )
                    ))
                    self.stdout.write(self.style.ERROR(
                        "   FAILURE: {}".format(
                            ", ".join(update_failed)
                        )
                    ))


def obj_type(geo_result):
    """
    Extracts the type of the object from the `_components` dictionary of the result.
    """
    return geo_result._components.get('_type') if geo_result.ok else None


def set_coord(geo_result_to, geo_result_from, angle, index=None):
    """
    Updates the bounding box of the result from the specified query.
    Angle is either 'ne' for North-East or 'sw' for South-West;
    Index is either 0 for east/west, 1 for north/south, or None for both.
    """
    translate = {'ne': 'northeast', 'sw': 'southwest'}
    pair = geo_result_from.bbox[translate[angle]] if geo_result_from.ok else [None, None]
    if index is not None:
        geo_result_to.bbox[translate[angle]][index] = pair[index]
    else:
        geo_result_to.bbox[translate[angle]] = pair
    geo_result_to.error = geo_result_to.error or getattr(geo_result_from, 'error', None)


def find_and_set_coord(geo_result, region, country_code, condition, angle, index=None, update_center=False):
    """
    Finds a specific result line upon geocoding the region name in the given country,
    according to the given condition (typically, the type of the result, such as 'state',
    'island', etc.; otherwise a callable for a more complex condition).
    Then updates the bounding box.
    """
    try:
        coords = next(filter(
            condition if callable(condition) else lambda r: obj_type(r) == condition,
            geocode(region, country=country_code, multiple=True)
        ))
    except StopIteration:
        geo_result.error = "{} region not found or network error".format(region)
    else:
        if not isinstance(angle, tuple):
            angle = ((angle, index),)
        for angle_bit, index_bit in angle:
            set_coord(geo_result, coords, angle_bit, index_bit)
        if update_center:
            geo_result.xy = coords.xy


def find_country(geo_result_to, geo_result_from):
    """
    Filters the geocoding results by object type 'country',
    then sorts the list by the latitude,
    and returns the first-most result.
    """
    geo_result_to.error = getattr(geo_result_from, 'error', not geo_result_from.ok)
    coords = sorted(
        filter(lambda r: obj_type(r) == 'country', geo_result_from),
        key=lambda r: r.bbox['northeast'][1] if r.bbox else 0
    )[0]
    geo_result_to.bbox, geo_result_to.xy = coords.bbox, coords.xy


def custom_calculation(country_code):
    """
    Some countries are just too complicated, and OpenCage is of no help...
    """
    class GeoResultStub(object):
        _components = {}
        bbox = {'northeast': [None, None], 'southwest': [None, None]}
        xy = [None, None]
        ok, error = True, False

        def __init__(self, country_code):
            self._components = {'ISO_3166-1_alpha-2': country_code, '_type': 'country'}

        def __iter__(self):
            self.exhausted = False
            return self

        def __next__(self):
            if self.exhausted:
                raise StopIteration
            else:
                self.exhausted = True
                return self

        def __len__(self):
            return 1

        def __str__(self):
            return "<[{}] Opencage - Manual Geocoding>".format("OK" if not self.error else "ERROR")

        def __repr__(self):
            return str(self)

        def set_default_result(self, index):
            pass

    result = None

    if country_code == 'AU':
        # Australia mainland.
        result = GeoResultStub('AU')
        find_and_set_coord(result, 'Queensland', 'AU', 'state', 'ne', None)
        find_and_set_coord(result, 'Western Australia', 'AU', 'state', 'sw', 0)
        find_and_set_coord(result, 'Tasmania', 'AU', lambda r: 'island' in r._components, 'sw', 1)
        # https://placenames.nt.gov.au/origins/centre-australia
        # https://en.wikipedia.org/wiki/List_of_extreme_points_of_Australia#Other_points
        result.xy = [134.354806, -25.610111]

    if country_code == 'CL':
        # Chile has some uninhabited islands far in the Pacific, distorting the bounding box.
        result = GeoResultStub('CL')
        coords = geocode('Provincia de la Antártica Chilena', country='CL')
        set_coord(result, coords, 'ne', 0)
        set_coord(result, coords, 'sw', 1)
        set_coord(result, geocode('Región Aysén del General Carlos Ibáñez del Campo', country='CL'), 'sw', 0)
        set_coord(result, geocode('Región de Arica y Parinacota', country='CL'), 'ne', 1)
        # https://en.wikipedia.org/wiki/List_of_extreme_points_of_Chile#Geographical_center
        result.xy = [-71.312389, -35.697472]

    if country_code == 'EC':
        # Equador has some islands in the Pacific, distorting the bounding box.
        result = GeoResultStub('EC')
        set_coord(result, geocode('Orellana', country='EC'), 'ne', 0)  # east
        set_coord(result, geocode('Manabí', country='EC'), 'sw', 0)  # west
        find_and_set_coord(result, 'Esmeraldas', 'EC', 'state', 'ne', 1)  # north
        set_coord(result, geocode('Zamora-Chinchipe', country='EC'), 'sw', 1)  # south
        result.xy = [
            round(((result.bbox['northeast'][0] or 0) + (result.bbox['southwest'][0] or 0)) / 2, 7),
            round(((result.bbox['northeast'][1] or 0) + (result.bbox['southwest'][1] or 0)) / 2, 7)
        ]

    if country_code == 'ES':
        # Only continental Spain boundaries, without the islands.
        result = GeoResultStub('ES')
        find_and_set_coord(result, 'Galicia', 'ES', 'state', (('ne', 1), ('sw', 0)))
        set_coord(result, geocode('Cataluña', country='ES'), 'ne', 0)
        set_coord(result, geocode('Andalucía', country='ES'), 'sw', 1)
        # https://en.wikipedia.org/wiki/List_of_extreme_points_of_Spain#Spanish_mainland
        result.xy = [-3.684234, 40.30926]

    if country_code == 'FR':
        # For now, the "Mainland France" trick works, but may not in the future.
        pass

    if country_code == 'MC':
        # We are not interested in the maritime EEA of Monaco, which is 10x times larger than Monaco itself.
        result = GeoResultStub('MC')
        find_and_set_coord(result, 'Monaco', 'MC', 'city', (('ne', None), ('sw', None)), update_center=True)

    if country_code == 'NO':
        # Only continental Norway boundaries, without the islands.
        result = GeoResultStub('NO')
        set_coord(result, geocode('Finnmark', country='NO'), 'ne')
        set_coord(result, geocode('Rogaland', country='NO'), 'sw', 0)
        set_coord(result, geocode('Vest-Agder', country='NO'), 'sw', 1)
        # https://en.wikipedia.org/wiki/Centre_of_Norway
        result.xy = [12.307778, 63.990556]

    if country_code == 'PT':
        # Only continental Portugal boundaries, without the islands.
        result = GeoResultStub('PT')
        set_coord(result, geocode('Terras de Trás-os-Montes', country='PT'), 'ne', 0)
        set_coord(result, geocode('Alto Minho', country='PT'), 'ne', 1)
        set_coord(result, geocode('Área Metropolitana de Lisboa', country='PT'), 'sw', 0)
        set_coord(result, geocode('Algarve', country='PT'), 'sw', 1)
        # https://pt.wikipedia.org/wiki/Centro_Geográfico#Portugal
        result.xy = [-8.130573, 39.694502]

    if country_code == 'SG':
        # We are not interested in the Pedra Branca rocks belonging to Singapore.
        result = GeoResultStub('SG')
        # 'Pulau Ujong' and 'Pulau Tekong' used to work perfectly fine, but not
        # anymore. Why? Because.
        set_coord(result, geocode('South East Community Development Council', country='SG'), 'ne', 0)
        set_coord(result, geocode('North West Community Development Council', country='SG'), 'ne', 1)
        set_coord(result, geocode('South West Community Development Council', country='SG'), 'sw')
        # http://hjtann.blogspot.com/2012/11/the-geographic-centre-of-singapore.html
        result.xy = [103.800000, 1.366667]

    if country_code == 'TV':
        # The bounding box returned by OpenCage for Tuvalu is incorrect, and no
        # queries could reliably geocode the country's parts (islets / atolls).
        result = GeoResultStub('TV')
        result.bbox = {'northeast': [179.871061, -5.642230], 'southwest': [176.078332, -10.791658]}
        result.xy = [179.198333, -8.521111]

    if country_code == 'US':
        # Would expect geocoding "contiguous United States" or "conterminous United States"
        # to return the boundaries of the US 48 states on the continent.
        result = GeoResultStub('US')
        set_coord(result, geocode('Maine', country='US'), 'ne', 0)
        set_coord(result, geocode('Minnesota', country='US'), 'ne', 1)
        set_coord(result, geocode('California', country='US'), 'sw', 0)
        set_coord(result, geocode('Florida', country='US'), 'sw', 1)
        # https://en.wikipedia.org/wiki/Geographic_center_of_the_contiguous_United_States
        result.xy = [-98.583333, 39.833333]

    if country_code == 'VN':
        result = GeoResultStub('VN')
        set_coord(result, geocode('Đông Bắc', country='VN'), 'ne', 1)
        set_coord(result, geocode('Tây Bắc', country='VN'), 'sw', 0)
        set_coord(result, geocode('Đồng Bằng Sông Cửu Long', country='VN'), 'sw', 1)
        set_coord(result, geocode('Duyên Hải Nam Trung Bộ', country='VN'), 'ne', 0)
        result.xy = [107.579167, 16.466667]

    if country_code in ('CY', 'JE', 'MY', 'PG', 'SY'):
        # For some countries, OpenCage for an unknown reason returns two results with
        # different bounding boxes (and one of them is usually incorrect or overly large).
        # In the case of Malaysia, we want both Peninsular and Malaysian Borneo regions.
        result = GeoResultStub(country_code)
        find_country(result, geocode(
            {
                'CY': 'Cyprus',
                'JE': 'Jersey',
                'MY': 'Malaysia',
                'PG': 'Papua New Guinea',
                'SY': 'Syria',
            }[country_code],
            multiple=True))

    if result and not result.error and any(
            point is None for point in result.bbox['northeast'] + result.bbox['southwest'] + result.xy):
        result.error = "Some of the coordinates could not be calculated."

    return result
