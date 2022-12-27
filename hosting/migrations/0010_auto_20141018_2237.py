# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import hosting.validators
import phonenumber_field.modelfields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0009_auto_20141013_1704'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='contactpreference',
            options={'verbose_name': 'contact preference', 'verbose_name_plural': 'contact preferences'},
        ),
        migrations.RenameField(
            model_name='place',
            old_name='max_host',
            new_name='max_guest',
        ),
        migrations.AlterField(
            model_name='condition',
            name='abbr',
            field=models.CharField(verbose_name='abbreviation', help_text="Official abbreviation as used in the book. E.g.: 'Nef.'", max_length=20),
        ),
        migrations.AlterField(
            model_name='condition',
            name='slug',
            field=models.SlugField(verbose_name='URL friendly name', default='-', null=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='phone',
            name='number',
            field=phonenumber_field.modelfields.PhoneNumberField(max_length=128, verbose_name='number'),
        ),
        migrations.AlterField(
            model_name='phone',
            name='profile',
            field=models.ForeignKey(to='hosting.Profile', verbose_name='profile', related_name='phones', on_delete=django.db.models.deletion.CASCADE),
        ),
        migrations.AlterField(
            model_name='place',
            name='city',
            field=models.CharField(verbose_name='city', help_text='e.g.: Rotterdam', validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps], blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='place',
            name='owner',
            field=models.ForeignKey(to='hosting.Profile', verbose_name='owner', related_name='owned_places', on_delete=django.db.models.deletion.CASCADE),
        ),
        migrations.AlterField(
            model_name='profile',
            name='title',
            field=models.CharField(verbose_name='title', choices=[('Mrs', 'Mrs'), ('Mr', 'Mr')], blank=True, max_length=5),
        ),
    ]
