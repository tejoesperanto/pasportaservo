import os
import csv
import tempfile
from subprocess import Popen, PIPE

from django.http.response import HttpResponse
from django.views import generic
from django.template.loader import get_template
from django.template.defaultfilters import yesno
from django.utils.translation import ugettext_lazy as _

from hosting.mixins import StaffMixin
from hosting.models import Place
from links.utils import create_unique_url


class PDFBookView(StaffMixin, generic.TemplateView):
    template_name = 'book/book.tex'
    pdf_file = 'book/templates/book/book.pdf'
    response_class = HttpResponse
    content_type = 'application/pdf'

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['nomo'] = "Pasporta Servo"
        return kwargs

    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault('content_type', self.content_type)
        response = self.response_class(**response_kwargs)
        pdf = self.generate_pdf(context)
        response.write(pdf)
        return response

    def generate_pdf(self, context):
        template = get_template(self.template_name)
        rendered_template = template.render(context).encode('utf-8')
        with tempfile.TemporaryDirectory() as tempdir:
            # Create subprocess, supress output with PIPE and
            # run latex twice to generate the TOC properly.
            for i in range(2):
                process = Popen(
                    ['xelatex', '-output-directory', tempdir],
                    stdin=PIPE,
                    stdout=PIPE,
                )
                process.communicate(rendered_template)
            # Finally read the generated pdf.
            with open(os.path.join(tempdir, 'texput.pdf'), 'rb') as f:
                pdf = f.read()
        return pdf

pdf_book = PDFBookView.as_view()


class ContactExport(StaffMixin, generic.ListView):
    model = Place
    response_class = HttpResponse
    content_type = 'text/csv'
    place_fields = ['in_book', 'checked', 'city', 'closest_city', 'address',
        'postcode', 'state_province', 'country', 'short_description',
        'tour_guide', 'have_a_drink', 'max_guest', 'max_night', 'contact_before']
    owner_fields = ['title', 'first_name', 'last_name', 'birth_date']
    user_fields = ['email', 'username', 'last_login', 'date_joined']
    phone_fields = ['phone1', 'phone2']
    other_fields = ['family_members', 'conditions', 'update_url', 'confirm_url']

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related('owner__user')
        qs = qs.filter(available=True, deleted=False)
        return qs

    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault('content_type', self.content_type)
        response = self.response_class(**response_kwargs)
        csv_file = self.generate_csv(context)
        response.write(csv_file)
        return response

    def generate_csv(self, context):
        with tempfile.TemporaryDirectory() as tempdir:
            with open(os.path.join(tempdir, 'contacts.csv'), 'w+') as f:
                writer = csv.writer(f)
                writer.writerow(self.user_fields + self.owner_fields +
                    self.place_fields + self.phone_fields + self.other_fields)
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
        phones = [phone.display() for phone in place.owner.phones.all()[:2]]
        others = [place.display_family_members(), place.display_conditions(),
            self.get_url(place, 'update'), self.get_url(place, 'confirm')]
        return from_user + from_owner + from_place + phones + others

    def build_row(self, obj, fields):
        row = []
        for f in fields:
            value = getattr(obj, f)
            try:
                row.append(value.strftime('%m/%d/%Y'))
            except AttributeError:
                if isinstance(value, bool):
                    value = yesno(value, "1,0")
                if f == 'title':
                    value = _(obj.title)
                row.append(value)
        return row

    def get_url(self, place, action):
        return create_unique_url({'place': place.pk, 'action': action})

contact_export = ContactExport.as_view()
