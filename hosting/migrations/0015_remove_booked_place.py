# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import hosting.validators


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0014_remove_profile_places'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='place',
            name='booked',
        ),
        migrations.AlterField(
            model_name='place',
            name='city',
            field=models.CharField(blank=True, help_text='Name in the official language, not in Esperanto (e.g.: Rotterdam)', max_length=255, verbose_name='city', validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='place',
            name='closest_city',
            field=models.CharField(blank=True, help_text='If you place is in a town near a bigger city. Name in the official language, not in Esperanto.', max_length=255, verbose_name='closest big city', validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='profile',
            name='first_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='first name', validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps, hosting.validators.validate_no_digit]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='profile',
            name='last_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='last name', validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps, hosting.validators.validate_no_digit]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='profile',
            name='title',
            field=models.CharField(blank=True, max_length=5, verbose_name='title', choices=[(None, ''), ('Mrs', 'Mrs'), ('Mr', 'Mr')]),
            preserve_default=True,
        ),
    ]
