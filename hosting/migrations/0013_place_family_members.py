# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0012_auto_20141110_1646'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='family_members',
            field=models.ManyToManyField(to='hosting.Profile', null=True, verbose_name='family members', blank=True),
            preserve_default=True,
        ),
    ]
