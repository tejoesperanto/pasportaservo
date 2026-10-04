import csv
import math
from distutils.dir_util import copy_tree
from os.path import isfile, join
from subprocess import call
from tempfile import mkdtemp
from typing import TYPE_CHECKING, TypeGuard, cast

from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.core.management.base import BaseCommand, CommandError
from django.db.models import QuerySet
from django.template import Context, Template
from django.utils import translation

import utm
from django_countries import countries
from django_countries.fields import Country

from core.utils import sort_by
from hosting.countries import countries_with_mandatory_region
from hosting.models import LocationType, Place, Whereabouts

COUNTRIES_WITH_REGIONS = (
    countries_with_mandatory_region() | {'BE', 'BR', 'CA', 'DE', 'FR', 'GB', 'US'}
)


class LatexCommand(BaseCommand if TYPE_CHECKING else object):
    template_name: str = 'PasportaServo.tex'
    address_only: bool = False
    make_pdf: bool = False
    tex_files: list[str] = [
        template_name,
        'pages/title.tex',
        'pages/address.tex',
    ]

    def activate_translation(self):
        translation.activate(settings.LANGUAGE_CODE)

    def handle(self, *args, **options):
        self.activate_translation()
        super().handle(*args, **options)

    def handle_label(self, country: str, **options):
        self.country = country.upper()
        if self.country == 'ALL':
            self.countries = sorted(set(
                Place.objects
                .filter(in_book=True, visibility__visible_in_book=True, checked=True)
                .values_list('country', flat=True)
            ))
            for country in self.countries[:8]:
                print(country)
                self.country = country
                self.make()
            return
        if self.country not in countries:
            raise CommandError(f"Unknown country: {self.country}")
        self.make()

    def make(self):
        prefix = f'ps-{self.country}-' if self.address_only else 'ps-'
        tempdir = mkdtemp(prefix=prefix)
        print("Copying in temp directory", tempdir)
        copy_tree('book/templates/book/', tempdir)
        self.context = self.get_context_data()
        print("Exporting latlng.csv...")
        self.export_latlng(tempdir)
        print("Rendering Tex files...")
        for template_name in self.tex_files:
            self.render_tex(tempdir, template_name)
        if self.make_pdf:
            n = 1 if self.address_only else 2
            for i in range(n):
                # Needs texlive-xetex
                call(['xelatex', 'PasportaServo.tex'], cwd=tempdir)
            if not isfile(join(tempdir, 'PasportaServo.pdf')):
                print("\nCould not generate the PDF")
            else:
                call(['evince', 'PasportaServo.pdf'], cwd=tempdir)
            print("\n", tempdir)

    def export_latlng(self, tempdir: str):
        with open(join(tempdir, 'latlng.csv'), 'w') as f:
            writer = csv.DictWriter(f, ['lat', 'lng'])
            writer.writeheader()
            place: Place
            for place in self.context['places']:
                if place.location and all(place.location.coords):
                    writer.writerow({'lat': place.location.y, 'lng': place.location.x})

    def get_objects(self):
        print("Grabbing data...")
        conditions = dict(
            in_book=True, visibility__visible_in_book=True,
            owner__death_date__isnull=True,
            checked=True,
        )
        places = Place.objects.filter(**conditions).order_by('city')
        if self.address_only:
            print("  for", self.country)
            places = places.filter(country=self.country)
        self._annotate_objects(places)

        return sort_by(
            ['closest_city', 'subregion.translated_or_latin_name', 'country.name'],
            places
        )

    def _annotate_objects(self, places: QuerySet[Place]):
        if TYPE_CHECKING:
            class TransformedWhereabouts(Whereabouts):
                utm_srid: int

        class NOT_CODED:  # TODO: Change to sentinel() in Python 3.15.
            def __bool__(self):
                return False

            def __repr__(self):
                return "NOT-CODED"

        def is_coded(
                value: 'TransformedWhereabouts | NOT_CODED | None'
        ) -> TypeGuard['TransformedWhereabouts']:
            return bool(value)

        locations_cache: dict[
            Country, dict[str, dict[str, 'TransformedWhereabouts | NOT_CODED']]
        ] = {}

        for place in places:
            closest_city_name = place.closest_city.upper()
            state = place.state_province.upper()
            if place.city.upper() == closest_city_name or not closest_city_name:
                # No need to calculate the distance to closest city.
                continue
            closest_city_location = (
                locations_cache.get(place.country, {})
                .get(state, {})
                .get(closest_city_name)
            )
            if closest_city_location is None:
                # Attempt reading from cache without the subregion.
                closest_city_location = (
                    locations_cache.get(place.country, {})
                    .get("", {})
                    .get(closest_city_name)
                )
            if closest_city_location is None:
                # Not cached yet, retrieve from database.
                positions = cast(
                    'QuerySet[TransformedWhereabouts]',
                    Whereabouts.objects.filter(
                        type=LocationType.CITY,
                        name=closest_city_name, country=place.country,
                    )
                )
                closest_city_location = positions.first() or NOT_CODED()
                locations_cache.setdefault(place.country, {})
                locations_cache[place.country].setdefault("", {})[
                    closest_city_name
                ] = closest_city_location
                # When the database holds multiple cities with the same name,
                # we must filter by the subregion.
                if len(positions) > 1:
                    closest_city_location = (
                        positions.filter(state=state).first() or NOT_CODED()
                    )
                    locations_cache[place.country].setdefault(state, {})[
                        closest_city_name
                    ] = closest_city_location
                # Transform the city's center point to a localized SRID
                # (Spatial Reference Identifier) so that distances can be
                # calculated in meters.
                if not isinstance(closest_city_location, NOT_CODED):
                    _, _, zone_number, zone_letter = utm.from_latlon(
                        closest_city_location.center.y, closest_city_location.center.x)
                    # The SRIDs based on UTM (Universal Transverse Mercator)
                    # coordinates are
                    # 327xx for the Southern hemisphere (zone letters A to M)
                    # 326xx for the Northern hemisphere (zone letter N to Z)
                    utm_srid = (32600 if zone_letter >= 'N' else 32700) + zone_number
                    closest_city_location.center.transform(utm_srid)
                    closest_city_location.utm_srid = utm_srid

            if not is_coded(closest_city_location) or not place.location:
                continue
            place_location: Point = (
                place.location.transform(closest_city_location.utm_srid, clone=True)
            )
            place.closest_city_distance = math.ceil(
                Distance(m=place_location.distance(closest_city_location.center)).km
            )

    def get_context_data(self):
        return {
            'year': 2026,
            'places': self.get_objects(),
            'INVALID_PREFIX': settings.INVALID_PREFIX,
            'ADDRESS_ONLY': self.address_only,
            'COUNTRIES_WITH_REGIONS': COUNTRIES_WITH_REGIONS,
        }

    def render_tex(self, tmp_path: str, template_name: str):
        with open(join(tmp_path, template_name), 'r') as f:
            template = Template(f.read())
        with open(join(tmp_path, template_name), 'w') as f:
            f.write(template.render(Context(self.context)))
