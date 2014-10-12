# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0006_auto_20141012_1022'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='website2',
            field=models.URLField(default='', blank=True, verbose_name='website 2'),
            preserve_default=False,
        ),
    ]
