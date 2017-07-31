import csv
from distutils.dir_util import copy_tree
from os.path import join, isfile
from tempfile import mkdtemp
from subprocess import call

from pyuca import Collator

from django.core.management.base import CommandError
from django.conf import settings
from django.utils import translation
from django.template import Template, Context

from django_countries import countries

from hosting.models import Place

c = Collator()


class LatexCommand(object):
    template_name = 'PasportaServo.tex'
    address_only = False
    make_pdf = False
    tex_files = [
        template_name,
        'pages/title.tex',
        'pages/address.tex',
    ]

    def activate_translation(self):
        translation.activate(settings.LANGUAGE_CODE)

    def handle(self, *args, **options):
        self.activate_translation()
        super().handle(*args, **options)

    def handle_label(self, country, **options):
        self.country = country.upper()
        if self.country == 'ALL':
            self.countries = sorted(set(Place.objects.filter(
                in_book=True, checked=True).values_list('country', flat=True)))
            for country in self.countries[:8]:
                print(country)
                self.country = country
                self.make()
            return
        if self.country not in countries:
            raise CommandError("Unknown country: {country}".format(self.country))
        self.make()

    def make(self):
        prefix = 'ps-{}-'.format(self.country) if self.address_only else 'ps-'
        tempdir = mkdtemp(prefix=prefix)
        print('Copying in temp directory', tempdir)
        copy_tree('book/templates/book/', tempdir)
        self.context = self.get_context_data()
        print('Exportorting latlng.csv...')
        self.export_latlng(tempdir)
        print('Rendering Tex files...')
        for template_name in self.tex_files:
            self.render_tex(tempdir, template_name)
        if self.make_pdf:
            n = 1 if self.address_only else 2
            for i in range(n):
                call(['xelatex', 'PasportaServo.tex'], cwd=tempdir)
            if not isfile(join(tempdir, 'PasportaServo.pdf')):
                print('\nCould not generate the PDF')
            else:
                call(['evince', 'PasportaServo.pdf'], cwd=tempdir)
            print('\n', tempdir)

    def export_latlng(self, tempdir):
        with open(join(tempdir, 'latlng.csv'), 'w') as f:
            writer = csv.DictWriter(f, ['lat', 'lng'])
            writer.writeheader()
            for place in self.context['places']:
                if all(place.location.coords):
                    writer.writerow({'lat': place.location.y, 'lng': place.location.x})

    def get_objects(self):
        print('Grabbing data...')
        places = Place.objects.filter(in_book=True, checked=True).order_by('city')
        if self.address_only:
            print('  for', self.country)
            places = places.filter(country=self.country)
        city_key = lambda place: c.sort_key(str(place.closest_city))
        region_key = lambda place: c.sort_key(str(place.state_province))
        country_key = lambda place: c.sort_key(str(place.country.name))
        return sorted(sorted(sorted(places, key=city_key), key=region_key), key=country_key)

    def get_context_data(self):
        return Context({
            'year': 2017,
            'places': self.get_objects(),
            'INVALID_PREFIX': settings.INVALID_PREFIX,
            'ADDRESS_ONLY': self.address_only,
            'COUNTRIES_WITH_REGIONS': settings.COUNTRIES_WITH_REGIONS,
        })

    def render_tex(self, tmp, template_name):
        with open(join(tmp, template_name), 'r') as f:
            template = Template(f.read())
        with open(join(tmp, template_name), 'w') as f:
            f.write(template.render(self.context))

