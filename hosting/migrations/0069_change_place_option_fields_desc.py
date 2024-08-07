# Generated by Django 3.2.25 on 2024-07-17 06:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0068_add_psuser_proxy_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='place',
            name='available',
            field=models.BooleanField(
                default=True,
                help_text="If there is a space to sleep on offer, you will be considered as a host.  You do not have to have a separate guestroom or even a bed. Detail your conditions in the description and via the 'conditions' dropdown list.",
                verbose_name='willing to host'),
        ),
        migrations.AlterField(
            model_name='place',
            name='have_a_drink',
            field=models.BooleanField(
                default=False,
                help_text='If you are ready to have a coffee or beer with visitors.',
                verbose_name='happy to have a drink'),
        ),
        migrations.AlterField(
            model_name='place',
            name='tour_guide',
            field=models.BooleanField(
                default=False,
                help_text='If you are ready to show your area to visitors.',
                verbose_name='happy to guide around'),
        ),
        migrations.AlterField(
            model_name='place',
            name='in_book',
            field=models.BooleanField(
                default=True,
                help_text='If you want this place to be in the printed book. It must have an available sleeping space for guests.',
                verbose_name='print in book'),
        ),
    ]
