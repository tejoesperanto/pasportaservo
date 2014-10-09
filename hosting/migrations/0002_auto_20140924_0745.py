# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='place',
            name='small_description',
        ),
        migrations.AddField(
            model_name='condition',
            name='abbr',
            field=models.CharField(max_length=20, help_text="Official abbreviation as used in the book. E.g.: 'Nef.'", default='', verbose_name='name'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='condition',
            name='slug',
            field=models.SlugField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='place',
            name='closest_city',
            field=models.CharField(blank=True, max_length=255, help_text='If you place is in a town near a bigger city.', default='', verbose_name='closest big city'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='place',
            name='have_a_drink',
            field=models.BooleanField(help_text='If you are ready to have a coffee or beer with visitors.', default=False, verbose_name='have a drink'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='place',
            name='short_description',
            field=models.CharField(blank=True, max_length=140, help_text='Used in the book, 140 character maximum.', default='', verbose_name='short description'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='place',
            name='tour_guide',
            field=models.BooleanField(help_text='If you are ready to show your area to visitors.', default=False, verbose_name='tour guide'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(blank=True, upload_to='avatars', default='', verbose_name='avatar'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='description',
            field=models.TextField(blank=True, help_text='All about yourself.', default='', verbose_name='description'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='first_name',
            field=models.CharField(blank=True, max_length=255, default='', verbose_name='first name'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='last_name',
            field=models.CharField(blank=True, max_length=255, default='', verbose_name='last name'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='condition',
            name='name',
            field=models.CharField(help_text="E.g.: 'Ne fumu'.", max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='phone',
            name='type',
            field=models.CharField(choices=[('m', 'Mobile'), ('h', 'Home'), ('w', 'Work')], max_length=3, default='m', verbose_name='phone type'),
        ),
        migrations.AlterField(
            model_name='place',
            name='address',
            field=models.CharField(help_text='e.g.: Nieuwe Binnenweg 176', max_length=255, verbose_name='address'),
        ),
        migrations.AlterField(
            model_name='place',
            name='available',
            field=models.BooleanField(help_text='If this place is searchable. If yes, you will be considered as host.', default=True, verbose_name='available'),
        ),
        migrations.AlterField(
            model_name='place',
            name='booked',
            field=models.BooleanField(help_text='If the place is currently booked.', default=False, verbose_name='booked'),
        ),
        migrations.AlterField(
            model_name='place',
            name='city',
            field=models.CharField(help_text='e.g.: Rotterdam', max_length=255, verbose_name='city'),
        ),
        migrations.AlterField(
            model_name='place',
            name='description',
            field=models.TextField(blank=True, help_text='Description or remarks about your place.', verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='place',
            name='in_book',
            field=models.BooleanField(help_text='If you want this place to be in the printed book. Must be available.', default=False, verbose_name='print in book'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='title',
            field=models.CharField(choices=[('Mrs', 'Mrs'), ('Mr', 'Mr')], max_length=5, verbose_name='title'),
        ),
    ]
