# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-06-03 00:23
from __future__ import unicode_literals

from django.db import migrations, models

import hosting.fields


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0048_profile_gender_pronoun'),
    ]

    operations = [
        # Help text for users to better understand the form field
        # Explicit db_column to avoid losing data due to a (non-versionable) change of ForeigKeyWithSuggestions' attname
        migrations.AlterField(
            model_name='profile',
            name='gender',
            field=hosting.fields.ForeigKeyWithSuggestions(blank=True, choices='hosting.Gender', db_column='gender_value', help_text='Type your preference or select one from the suggestions.', to_field='name', verbose_name='gender'),
        ),
        # Additional and more inclusive pronouns
        migrations.AlterField(
            model_name='profile',
            name='pronoun',
            field=models.CharField(blank=True, choices=[(None, ''), ('She', 'she'), ('He', 'he'), ('They', 'they'), ('Ze', 'ze'), ('They/She', 'they or she'), ('They/He', 'they or he'), ('Ze/She', 'ze or she'), ('Ze/He', 'ze or he'), ('Any', 'any')], max_length=10, verbose_name='personal pronoun'),
        ),
    ]
