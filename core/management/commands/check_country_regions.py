from django.core.management.base import BaseCommand
from django.db.models import Q

from hosting.countries import COUNTRIES_DATA
from hosting.models import CountryRegion, Place


class Command(BaseCommand):
    help = """
        Checks for invalid addresses in the database in terms of administrative units
        (states, provinces, districts) of the given country.
        """

    def add_arguments(self, parser):
        parser.add_argument(
            'country',
            choices=tuple(sorted(COUNTRIES_DATA.keys())),
            metavar='country_ISO_code',
            help="the country code to check for invalid addresses.")

    def handle(self, *args, **options):
        country_code = options['country']

        country_regions = CountryRegion.objects.filter(country=country_code).values('iso_code')
        region_is_mandatory = (
            'administrativeArea' in COUNTRIES_DATA[country_code].get('required_fields', [])
        )
        if country_regions:
            valid_address = Q(state_province__in=country_regions)
            if not region_is_mandatory:
                valid_address |= Q(state_province="")
            places = Place.all_objects.filter(country=country_code).exclude(valid_address)
        else:
            places = Place.all_objects.none()
        if places:
            print_regions = "; ".join(sorted([
                f"{iso_code} ({latin_name or latin_code})"
                for (iso_code, latin_code, latin_name)
                in country_regions.values_list('iso_code', 'latin_code', 'latin_name')
            ]))
            self.stdout.write(
                ("Mandatory" if region_is_mandatory else "Allowed")
                + f" values: {print_regions}\n\n"
            )
        for p in places:
            deletion_note = " [DEL]" if p.deleted else ""
            self.stdout.write(f"{p!r}{deletion_note} -- {p.state_province or 'empty'}")

        if not places:
            self.stdout.write(self.style.SUCCESS("** All addresses are valid.\n"))
        else:
            self.stdout.write("\n")
