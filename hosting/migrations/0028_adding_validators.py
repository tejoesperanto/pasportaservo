# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-24 20:35
from __future__ import unicode_literals

from django.db import migrations, models

import hosting.validators


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0027_profile_names_inversed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='place',
            name='closest_city',
            field=models.CharField(blank=True, help_text='If your place is in a town near a bigger city. Name in the official language, not in Esperanto.', max_length=255, validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps], verbose_name='closest big city'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='birth_date',
            field=models.DateField(blank=True, help_text='In the format year(4 digits)-month(2 digits)-day(2 digits).', null=True, validators=[hosting.validators.TooFarPastValidator(200), hosting.validators.validate_not_in_future], verbose_name='birth date'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='first_name',
            field=models.CharField(blank=True, max_length=255, validators=[hosting.validators.validate_not_too_many_caps, hosting.validators.validate_no_digit, hosting.validators.validate_latin], verbose_name='first name'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='last_name',
            field=models.CharField(blank=True, max_length=255, validators=[hosting.validators.validate_not_too_many_caps, hosting.validators.validate_no_digit, hosting.validators.validate_latin], verbose_name='last name'),
        ),
    ]
