import csv
from tempfile import NamedTemporaryFile

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import translation


class Command(BaseCommand):
    def handle(self, *args, **options):
        translation.activate('eo')
        f = NamedTemporaryFile(mode='w+', delete=False, suffix='.csv')
        book = Group.objects.get(name='libro2017')
        writer = csv.writer(f)
        users = (
            User.objects.filter(groups__name='libro2017')
            & User.objects.exclude(reservation__isnull=True)
        ).order_by('reservation__amount', 'first_name').distinct()
        for user in users:
            writer.writerow([
                user.profile.full_name,
                user.email,
                user.profile.rawdisplay_phones(),
                'En la libro' if book in user.groups.all() else 'ne',
                repr(user.reservation_set.first()),
                'http://pspt.se' + user.profile.get_absolute_url(),
            ])
        print(f.name)
