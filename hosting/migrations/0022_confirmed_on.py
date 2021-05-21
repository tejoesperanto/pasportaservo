# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-10-12 18:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosting", "0021_update_availability"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="phone",
            name="confirmed",
        ),
        migrations.RemoveField(
            model_name="place",
            name="confirmed",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="confirmed",
        ),
        migrations.RemoveField(
            model_name="website",
            name="confirmed",
        ),
        migrations.AddField(
            model_name="phone",
            name="confirmed_on",
            field=models.DateTimeField(
                blank=True, default=None, null=True, verbose_name="confirmed on"
            ),
        ),
        migrations.AddField(
            model_name="place",
            name="confirmed_on",
            field=models.DateTimeField(
                blank=True, default=None, null=True, verbose_name="confirmed on"
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="confirmed_on",
            field=models.DateTimeField(
                blank=True, default=None, null=True, verbose_name="confirmed on"
            ),
        ),
        migrations.AddField(
            model_name="website",
            name="confirmed_on",
            field=models.DateTimeField(
                blank=True, default=None, null=True, verbose_name="confirmed on"
            ),
        ),
    ]
