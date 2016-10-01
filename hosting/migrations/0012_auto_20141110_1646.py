# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import hosting.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0011_auto_20141030_1201'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(validators=[hosting.validators.validate_image, hosting.validators.validate_size], upload_to='avatars', blank=True, help_text='Small image under 100kB. Ideal size: 140x140 px.', verbose_name='avatar'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(null=True, blank=True, to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
    ]
