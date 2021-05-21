# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-06-07 16:21
from __future__ import unicode_literals

from django.db import migrations, models


def update_locations_confidence(app_registry, schema_editor):
    """
    We don't want to make existing points on map disappear, but we also
    don't know if they were calculated by algorithm or selected manually,
    so we're choosing a conservative value for confidence higher than 1.
    """
    Place = app_registry.get_model("hosting", "Place")
    Place.all_objects.filter(location__isnull=False).update(location_confidence=2)


class Migration(migrations.Migration):

    dependencies = [
        ("hosting", "0049_profile_gender_pronoun"),
    ]

    operations = [
        migrations.AddField(
            model_name="place",
            name="location_confidence",
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name="confidence"
            ),
        ),
        migrations.RunPython(
            update_locations_confidence, reverse_code=migrations.RunPython.noop
        ),
    ]
