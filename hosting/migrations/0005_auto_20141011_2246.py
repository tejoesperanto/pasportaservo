# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0004_auto_20141011_1737'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='checked',
            field=models.BooleanField(verbose_name='checked', default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='place',
            name='deleted',
            field=models.BooleanField(verbose_name='deleted', default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='place',
            name='state_province',
            field=models.CharField(default='', blank=True, verbose_name='State / Province', max_length=70),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='place',
            name='address',
            field=models.TextField(blank=True, help_text='e.g.: Nieuwe Binnenweg 176', verbose_name='address'),
        ),
        migrations.AlterField(
            model_name='place',
            name='postcode',
            field=models.CharField(blank=True, verbose_name='postcode', max_length=11),
        ),
    ]
