# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0013_place_family_members'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='places',
        ),
    ]
