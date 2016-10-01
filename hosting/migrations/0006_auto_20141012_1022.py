# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0005_auto_20141011_2246'),
    ]

    operations = [
        migrations.AddField(
            model_name='phone',
            name='checked',
            field=models.BooleanField(default=False, verbose_name='checked'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='phone',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='place',
            name='owner',
            field=models.ForeignKey(default=1, verbose_name='owner', to='hosting.Profile', on_delete=django.db.models.deletion.CASCADE),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='checked',
            field=models.BooleanField(default=False, verbose_name='checked'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='profile',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='profile',
            name='website',
            field=models.URLField(default='', blank=True, verbose_name='website'),
            preserve_default=False,
        ),
    ]
