from os.path import join
import csv
from shutil import copytree
from operator import attrgetter
import tempfile
from subprocess import call, PIPE

from django.http.response import HttpResponse
from django.views import generic
from django.template import Template, Context
from django.template.defaultfilters import yesno
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from hosting.mixins import StaffMixin
from hosting.models import Place
from links.utils import create_unique_url

from pyuca import Collator
c = Collator()

class PDFBookView(StaffMixin, generic.TemplateView):
    template_name = 'PasportaServo.tex'
    pages = [
        'pages/title.tex',
        'pages/address.tex',
    ]
    response_class = HttpResponse
    content_type = 'application/pdf'

    def get_objects(self):
        places = Place.objects.filter(
            country='FR',
            in_book=True,
            checked=True)
        city_key = lambda place: c.sort_key(str(place.closest_city))
        region_key = lambda place: c.sort_key(str(place.state_province))
        country_key = lambda place: c.sort_key(str(place.country.name))
        return sorted(sorted(sorted(places, key=city_key), key=region_key), key=country_key)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['year'] = 2017
        context['places'] = self.get_objects()
        return context

    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault('content_type', self.content_type)
        response = self.response_class(**response_kwargs)
        self.context = Context(context)
        pdf = self.generate_pdf()
        response.write(pdf)
        return response

    def render_tex(self, tmp, template_name):
        with open(join(tmp, template_name), 'r') as f:
            template = Template(f.read())
        with open(join(tmp, template_name), 'w') as f:
            f.write(template.render(self.context))

    def generate_pdf(self):
        with tempfile.TemporaryDirectory() as tempdir:
            tmp = copytree('book/templates/book/', join(tempdir, 'book'))
            self.render_tex(tmp, self.template_name)
            for template in self.pages:
                self.render_tex(tmp, template)
            # Create subprocess, supress output with PIPE and
            # run latex twice to generate the TOC properly.
            for i in range(2):
                process = call(
                    ['xelatex', self.template_name],
                    cwd=tmp,
                    stdin=PIPE,
                    stdout=PIPE,
                )
                # process.communicate(rendered_template)
            import time; time.sleep(6)
            # Finally read the generated pdf.
            with open(join(tmp, 'PasportaServo.pdf'), 'rb') as f:
                pdf = f.read()
        return pdf

pdf_book = PDFBookView.as_view()


class ContactExport(StaffMixin, generic.ListView):
    response_class = HttpResponse
    content_type = 'text/csv'
    place_fields = ['in_book', 'checked', 'city', 'closest_city', 'address',
        'postcode', 'state_province', 'country', 'short_description',
        'tour_guide', 'have_a_drink', 'max_guest', 'max_night', 'contact_before', 'confirmed_on']
    owner_fields = ['title', 'first_name', 'last_name', 'birth_date']
    user_fields = ['email', 'username', 'last_login', 'date_joined']
    other_fields = ['phones', 'family_members', 'conditions', 'update_url', 'confirm_url']

    def get_queryset(self):
        places = Place.objects.prefetch_related('owner__user')
        places = places.filter(available=True).exclude(
            owner__user__email__startswith=settings.INVALID_PREFIX
        )
        return places

    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault('content_type', self.content_type)
        response = self.response_class(**response_kwargs)
        csv_file = self.generate_csv(context)
        response.write(csv_file)
        return response

    def generate_csv(self, context):
        with tempfile.TemporaryDirectory() as tempdir:
            with open(join(tempdir, 'contacts.csv'), 'w+') as f:
                writer = csv.writer(f)
                writer.writerow(self.user_fields + self.owner_fields +
                                self.place_fields + self.other_fields)
                for place in context['place_list']:
                    row = self.get_row(place)
                    writer.writerow(row)
                f.seek(0)
                return f.read()

    def get_row(self, place):
        from_user, from_owner, from_place = [], [], []
        from_user = self.build_row(place.owner.user, self.user_fields)
        from_owner = self.build_row(place.owner, self.owner_fields)
        from_place = self.build_row(place, self.place_fields)
        others = [
            place.owner.rawdisplay_phones(),
            place.rawdisplay_family_members(),
            place.rawdisplay_conditions(),
            self.get_url(place, 'update'),
            self.get_url(place, 'confirm'),
        ]
        return from_user + from_owner + from_place + others

    def build_row(self, obj, fields):
        row = []
        for f in fields:
            value = getattr(obj, f)
            try:
                row.append(value.strftime('%m/%d/%Y'))
            except AttributeError:
                if isinstance(value, bool):
                    value = yesno(value, _("yes,no"))
                if f == 'title':
                    value = _(obj.title)
                if f == 'confirmed_on':
                    value = '01/01/1970'
                row.append(value)
        return row

    def get_url(self, place, action):
        return create_unique_url({'place': place.pk, 'action': action})

contact_export = ContactExport.as_view()
