# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('hosting', '0010_auto_20141018_2237'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='authorized_users',
            field=models.ManyToManyField(help_text='List of users authorized to view most of data of this accommodation.', to=settings.AUTH_USER_MODEL, null=True, verbose_name='authorized users', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='place',
            name='max_guest',
            field=models.PositiveSmallIntegerField(null=True, verbose_name='maximum number of guest', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='profile',
            name='description',
            field=models.TextField(help_text='Short biography.', verbose_name='description', blank=True),
            preserve_default=True,
        ),
    ]
