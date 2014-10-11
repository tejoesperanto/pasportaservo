# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0003_auto_20141010_1056'),
    ]

    operations = [
        migrations.AddField(
            model_name='phone',
            name='comments',
            field=models.CharField(blank=True, verbose_name='comments', default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='phone',
            name='country',
            field=django_countries.fields.CountryField(verbose_name='country', default='', max_length=2),
            preserve_default=False,
        ),
    ]
