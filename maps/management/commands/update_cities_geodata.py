from django.contrib.gis.geos import LineString, Point
from django.core.management.base import BaseCommand
from django.db.models import (
    Case, CharField, Value as V, When, functions as dbf,
)

from hosting.models import LOCATION_CITY, Place, Whereabouts
from hosting.utils import geocode_city

from ... import COUNTRIES_WITH_MANDATORY_REGION, SRID


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
            .annotate(lookup=dbf.Concat('name', V('###'), 'state', V('###'), 'country', output_field=CharField()))
            .filter(type=LOCATION_CITY)
            .values_list('lookup', flat=True)
        )
        city_list = (
            Place.all_objects
            .annotate(city_lookup=dbf.Concat(
                dbf.Upper('city'),
                V('###'),
                Case(
                    When(country__in=COUNTRIES_WITH_MANDATORY_REGION, then=dbf.Upper('state_province')),
                    default=V('')
                ),
                V('###'),
                'country',
                output_field=CharField()))
            .exclude(city='')
            .exclude(city_lookup__in=mapped_cities)
        )

        success_counter = 0
        for place in city_list:
            city_location = geocode_city(place.city, state_province=place.state_province, country=place.country.code)
            if city_location:
                whereabouts = Whereabouts.objects.create(
                    type=LOCATION_CITY,
                    name=place.city.upper(),
                    state=place.state_province.upper() if place.country in COUNTRIES_WITH_MANDATORY_REGION else '',
                    country=place.country,
                    bbox=LineString(city_location.bbox['southwest'], city_location.bbox['northeast'], srid=SRID),
                    center=Point(city_location.xy, srid=SRID),
                )
                if self.verbosity >= 2:
                    self.stdout.write("+ Mapped {!r}".format(whereabouts))
                success_counter += 1
            else:
                if self.verbosity >= 2:
                    self.stdout.write("- {city} ({country}) could not be mapped".format(
                        city=place.city, country=place.country
                    ))

            if city_location is not None and city_location.remaining_api_calls < 500:
                self.stdout.write(self.style.ERROR(
                    "Daily geocoding requests limit exhausted. Please continue on a different day!"
                ))
                break

        if self.verbosity >= 1:
            self.stdout.write(self.style.HTTP_INFO("[MAPPED {} CITIES]".format(success_counter)))
