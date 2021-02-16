from django.contrib.gis.geos import LineString, Point
from django.core.management.base import BaseCommand
from django.db.models import (
    Case, CharField, Value as V, When, functions as dbf,
)
from django.utils.termcolors import make_style

from hosting.countries import countries_with_mandatory_region
from hosting.models import LocationType, Place, Whereabouts
from hosting.utils import geocode_city

from ... import SRID


class Command(BaseCommand):
    help = """
        Maps the cities within the current database.  Updates the geo-data
        (bounding boxes and center points) of only those cities which were
        not mapped yet,  and up to 2000 geocoding requests (because of the
        OpenCage's daily limit).
        """

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']

        mapped_cities = (
            Whereabouts.objects
            .annotate(lookup=dbf.Concat(
                'name', V('###'), 'state', V('###'), 'country',
                output_field=CharField()))
            .filter(type=LocationType.CITY)
            .values_list('lookup', flat=True)
        )
        city_list = (
            Place.all_objects
            .annotate(city_lookup=dbf.Concat(
                dbf.Upper('city'),
                V('###'),
                Case(
                    When(country__in=countries_with_mandatory_region(), then=dbf.Upper('state_province')),
                    default=V('')
                ),
                V('###'),
                'country',
                output_field=CharField()))
            .exclude(city='')
            .exclude(city_lookup__in=mapped_cities)
        )

        success_counter = 0
        mapped_set = set()
        for place in city_list:
            if place.city_lookup not in mapped_set:
                city_location = geocode_city(
                    place.city,
                    state_province=place.subregion.latin_name or place.subregion.latin_code,
                    country=place.country.code)
                if city_location:
                    whereabouts = Whereabouts.objects.create(
                        type=LocationType.CITY,
                        name=place.city.upper(),
                        state=(
                            place.state_province.upper()
                            if place.country in countries_with_mandatory_region()
                            else ''),
                        country=place.country,
                        bbox=LineString(
                            city_location.bbox['southwest'], city_location.bbox['northeast'],
                            srid=SRID),
                        center=Point(city_location.xy, srid=SRID),
                    )
                    if self.verbosity >= 2:
                        self.stdout.write(make_style(fg='green')(f"+ Mapped {whereabouts!r}"))
                    success_counter += 1
                else:
                    if self.verbosity >= 2:
                        region = f"R:{place.subregion.iso_code}, " if place.subregion.pk else ""
                        self.stdout.write(f"- {place.city} ({region}{place.country}) could not be mapped")
                mapped_set.add(place.city_lookup)
            else:
                city_location = None
                if self.verbosity >= 3:
                    self.stdout.write(
                        f"* {place.city} ({place.country}) skipped (already processed in this session)"
                    )

            if city_location is not None and city_location.remaining_api_calls < 500:
                self.stdout.write(self.style.ERROR(
                    "Daily geocoding requests limit exhausted. Please continue on a different day!"
                ))
                break

        if self.verbosity >= 1:
            self.stdout.write(make_style(opts=('bold',), fg='white')(
                f"[MAPPED {success_counter} CITIES]"
            ))
