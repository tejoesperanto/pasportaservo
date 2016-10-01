# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_extensions.db.fields
import django.utils.timezone
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0007_profile_website2'),
    ]

    operations = [
        migrations.CreateModel(
            name='Website',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('created', django_extensions.db.fields.CreationDateTimeField(blank=True, editable=False, verbose_name='created', default=django.utils.timezone.now)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(blank=True, editable=False, verbose_name='modified', default=django.utils.timezone.now)),
                ('url', models.URLField(verbose_name='URL')),
                ('checked', models.BooleanField(verbose_name='checked', default=False)),
                ('deleted', models.BooleanField(verbose_name='deleted', default=False)),
                ('profile', models.ForeignKey(verbose_name='profile', to='hosting.Profile', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'verbose_name_plural': 'websites',
                'verbose_name': 'website',
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='profile',
            name='phones',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='website',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='website2',
        ),
        migrations.AddField(
            model_name='phone',
            name='profile',
            field=models.ForeignKey(verbose_name='profile', default=1, to='hosting.Profile', on_delete=django.db.models.deletion.CASCADE),
            preserve_default=False,
        ),
    ]
