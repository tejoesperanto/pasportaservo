# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import hosting.validators


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0002_auto_20140924_0745'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phone',
            name='type',
            field=models.CharField(default='m', choices=[('m', 'mobile'), ('h', 'home'), ('w', 'work')], max_length=3, verbose_name='phone type'),
        ),
        migrations.AlterField(
            model_name='place',
            name='city',
            field=models.CharField(help_text='e.g.: Rotterdam', verbose_name='city', max_length=255, validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps]),
        ),
        migrations.AlterField(
            model_name='place',
            name='closest_city',
            field=models.CharField(help_text='If you place is in a town near a bigger city.', verbose_name='closest big city', max_length=255, validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps], blank=True),
        ),
        migrations.AlterField(
            model_name='place',
            name='postcode',
            field=models.CharField(verbose_name='postcode', max_length=11),
        ),
        migrations.AlterField(
            model_name='profile',
            name='first_name',
            field=models.CharField(verbose_name='first name', max_length=255, validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps], blank=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='last_name',
            field=models.CharField(verbose_name='last name', max_length=255, validators=[hosting.validators.validate_not_all_caps, hosting.validators.validate_not_too_many_caps], blank=True),
        ),
    ]
