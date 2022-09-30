import csv
import tempfile
from os.path import join

from django.conf import settings
from django.db.models import Q
from django.http.response import HttpResponse
from django.template.defaultfilters import yesno
from django.utils.translation import gettext_lazy as _
from django.views import generic

from core.auth import AuthMixin, AuthRole
from hosting.models import Place
from links.utils import create_unique_url


class ContactExportView(AuthMixin, generic.ListView):
    response_class = HttpResponse
    content_type = 'text/csv'
    display_permission_denied = False
    exact_role = AuthRole.ADMIN

    place_fields = [
        'in_book', 'checked', 'city', 'closest_city', 'address',
        'postcode', 'state_province', 'country', 'short_description',
        'tour_guide', 'have_a_drink', 'max_guest', 'max_night', 'contact_before',
        'confirmed_on',
    ]
    owner_fields = ['title', 'first_name', 'last_name', 'gender', 'birth_date']
    user_fields = ['email', 'username', 'last_login', 'date_joined']
    other_fields = ['phones', 'family_members', 'conditions', 'update_url', 'confirm_url']

    def dispatch(self, request, *args, **kwargs):
        kwargs['auth_base'] = None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        places = Place.objects.prefetch_related('owner__user')
        places = places.filter(available=True).exclude(
            Q(owner__user__email__startswith=settings.INVALID_PREFIX)
            | Q(owner__death_date__isnull=False)
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
                writer.writerow(self.user_fields + self.owner_fields + self.place_fields + self.other_fields)
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
                if f == 'postcode':
                    value = obj.get_postcode_display()
                if f == 'state_province':
                    value = obj.subregion.latin_code
                if f == 'confirmed_on':
                    value = "01/01/1970"
                row.append(value.strip() if isinstance(value, str) else value)
        return row

    def get_url(self, place, action):
        return create_unique_url({'place': place.pk, 'action': action})[0]
