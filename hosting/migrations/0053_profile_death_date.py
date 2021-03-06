# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-05-17 05:17
from __future__ import unicode_literals

from django.db import migrations, models
import hosting.validators


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0052_traveladvice_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='death_date',
            field=models.DateField(blank=True, help_text='In the format year(4 digits)-month(2 digits)-day(2 digits).', null=True, validators=[hosting.validators.validate_not_in_future], verbose_name='death date'),
        ),
    ]
