# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-10-10 15:51
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0050_place_location_confidence'),
    ]

    operations = [
        migrations.CreateModel(
            name='Whereabouts',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('C', 'City'), ('R', 'State / Province')], max_length=1, verbose_name='location type')),
                ('name', models.CharField(help_text='Name in the official language, not in Esperanto (e.g.: Rotterdam)', max_length=255, verbose_name='name')),
                ('state', models.CharField(blank=True, max_length=70, verbose_name='State / Province')),
                ('country', django_countries.fields.CountryField(max_length=2, verbose_name='country')),
                ('bbox', django.contrib.gis.db.models.fields.LineStringField(help_text='Expected diagonal: south-west lon/lat, north-east lon/lat.', srid=4326, verbose_name='bounding box')),
                ('center', django.contrib.gis.db.models.fields.PointField(help_text='Expected: longitude/latitude position.', srid=4326, verbose_name='geographical center')),
            ],
            options={
                'verbose_name': 'whereabouts',
                'verbose_name_plural': 'whereabouts',
            },
        ),
    ]
