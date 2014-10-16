# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0008_auto_20141012_1735'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactPreference',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(verbose_name='name', max_length=255)),
            ],
            options={
                'verbose_name': 'condition',
                'verbose_name_plural': 'conditions',
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='condition',
            name='created',
        ),
        migrations.RemoveField(
            model_name='condition',
            name='modified',
        ),
        migrations.AddField(
            model_name='profile',
            name='contact_preferences',
            field=models.ManyToManyField(blank=True, to='hosting.ContactPreference', verbose_name='contact preferences'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='phone',
            name='type',
            field=models.CharField(choices=[('m', 'mobile'), ('h', 'home'), ('w', 'work'), ('f', 'fax')], max_length=3, default='m', verbose_name='phone type'),
        ),
    ]
