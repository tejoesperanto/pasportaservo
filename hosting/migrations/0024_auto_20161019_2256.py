# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-10-19 22:56
from __future__ import unicode_literals

from django.db import migrations, models
import hosting.validators


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0023_abstract_model'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='place',
            options={'default_manager_name': 'all_objects', 'verbose_name': 'place', 'verbose_name_plural': 'places'},
        ),
        migrations.AlterField(
            model_name='profile',
            name='birth_date',
            field=models.DateField(blank=True, null=True, validators=[hosting.validators.TooFarPastValidator(200), hosting.validators.validate_not_in_future], verbose_name='birth date'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='first_name',
            field=models.CharField(blank=True, max_length=255, validators=[hosting.validators.validate_not_too_many_caps, hosting.validators.validate_no_digit], verbose_name='first name'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='last_name',
            field=models.CharField(blank=True, max_length=255, validators=[hosting.validators.validate_not_too_many_caps, hosting.validators.validate_no_digit], verbose_name='last name'),
        ),
    ]
