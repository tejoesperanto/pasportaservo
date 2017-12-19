# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0015_remove_booked_place'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='phone',
            unique_together=set([('profile', 'number')]),
        ),
    ]
