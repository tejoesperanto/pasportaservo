# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-09-21 12:45
from __future__ import unicode_literals

import django_extensions.db.fields
import phonenumber_field.modelfields
from django.conf import settings
from django.db import migrations, models

import hosting.utils
import hosting.validators


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0016_auto_20141123_2151'),
    ]

    operations = [
        migrations.AddField(
            model_name='phone',
            name='confirmed',
            field=models.BooleanField(default=False, verbose_name='confirmed'),
        ),
        migrations.AddField(
            model_name='place',
            name='confirmed',
            field=models.BooleanField(default=False, verbose_name='confirmed'),
        ),
        migrations.AddField(
            model_name='profile',
            name='confirmed',
            field=models.BooleanField(default=False, verbose_name='confirmed'),
        ),
        migrations.AddField(
            model_name='website',
            name='confirmed',
            field=models.BooleanField(default=False, verbose_name='confirmed'),
        ),
        migrations.AlterField(
            model_name='phone',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='phone',
            name='modified',
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
        ),
        migrations.AlterField(
            model_name='phone',
            name='number',
            field=phonenumber_field.modelfields.PhoneNumberField(help_text='International number format begining with the plus sign (e.g.: +31 10 436 1044)', max_length=128, verbose_name='number'),
        ),
        migrations.AlterField(
            model_name='place',
            name='authorized_users',
            field=models.ManyToManyField(blank=True, help_text='List of users authorized to view most of data of this accommodation.', to=settings.AUTH_USER_MODEL, verbose_name='authorized users'),
        ),
        migrations.AlterField(
            model_name='place',
            name='conditions',
            field=models.ManyToManyField(blank=True, to='hosting.Condition', verbose_name='conditions'),
        ),
        migrations.AlterField(
            model_name='place',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='place',
            name='family_members',
            field=models.ManyToManyField(blank=True, to='hosting.Profile', verbose_name='family members'),
        ),
        migrations.AlterField(
            model_name='place',
            name='modified',
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
        ),
        migrations.AlterField(
            model_name='place',
            name='short_description',
            field=models.CharField(blank=True, help_text='Used in the book and on profile, 140 characters maximum.', max_length=140, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(blank=True, help_text='Small image under 100kB. Ideal size: 140x140 px.', upload_to=hosting.utils.UploadAndRenameAvatar('avatars'), validators=[hosting.validators.validate_image, hosting.validators.validate_size], verbose_name='avatar'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='modified',
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
        ),
        migrations.AlterField(
            model_name='website',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='website',
            name='modified',
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
        ),
    ]
