# Generated by Django 3.2.15 on 2022-12-27 21:19

from django.core.management.color import no_style
from django.db import connection, migrations, models
from django.utils.text import slugify


def update_existing_conditions(apps, schema_editor):
    Condition = apps.get_model('hosting', 'Condition')
    data = (
        {
            'slug': "dont-smoke",
            'category': 'in_house',
            'name_en': "Don’t smoke",
            'name': "Ne fumu",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-2x fa-regular fa-circle condition-aux-color"></span>
                    <span class="fa fa-stack-1x fa-smoking condition-main-color" style="top: -0.1em"></span>
                    <span class="fa fa-stack-1x fa-slash condition-aux-color"></span>
                </span>
            """,
        },
        {
            'slug': "one-room",
            'category': 'sleeping_cond',
            'name_en': "One room apartment",
            'name': "Unuĉambra loĝejo",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-regular fa-money-bill-1 fa-lg condition-main-color"></span>
                </span>
            """,
        },
        {
            'slug': "sleeping-bag",
            'category': 'sleeping_cond',
            'name_en': "Bring a sleeping bag",
            'name': "Kunportu dormsakon",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x ps-sleeping-bag fa-lg condition-main-color" style="top: -0.07em"></span>
                </span>
            """,
        },
    )
    for condition_data in data:
        Condition.objects.update_or_create(slug=condition_data['slug'], defaults=condition_data)


def revert_existing_conditions(apps, schema_editor):
    Condition = apps.get_model('hosting', 'Condition')
    for condition in Condition.objects.all():
        condition.slug = slugify(condition.name_en)
        condition.save()


def add_new_conditions(apps, schema_editor):
    Condition = apps.get_model('hosting', 'Condition')
    data = (
        {
            'category': 'in_house',
            'name_en': "Smokers in house",
            'name': "Fumantoj hejme",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-smoking condition-main-color" style="top: -0.25em;"></span>
                </span>
            """,
        },
        {
            'category': 'in_house',
            'name_en': "Don’t use drugs",
            'name': "Ne uzu drogojn",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-2x fa-regular fa-circle condition-aux-color"></span>
                    <span class="fa fa-stack-1x fa-cannabis condition-main-color"></span>
                    <span class="fa fa-stack-1x fa-slash condition-aux-color"></span>
                </span>
            """,
        },
        {
            'category': 'in_house',
            'name_en': "Alcohol is not welcome",
            'name': "Alkoholo ne estas bonvena",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-2x fa-regular fa-circle condition-aux-color"></span>
                    <span class="fa fa-stack-1x fa-wine-bottle condition-main-color"></span>
                    <span class="fa fa-stack-1x fa-slash condition-aux-color"></span>
                </span>
            """,
        },
        {
            'category': 'in_house',
            'name_en': "Pets in house",
            'name': "Hejmaj bestoj",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-paw condition-main-color fa-sm" style="left: -0.45em; top: -0.45em;"></span>
                    <span class="fa fa-stack-1x fa-paw condition-main-color fa-sm" style="right: -0.5em; bottom: -0.45em; left: unset; transform: rotate(16deg);"></span>
                </span>
            """,
        },
        {
            'category': 'in_house',
            'name_en': "Unusual creatures in house",
            'name': "Nekutimaj bestoj en domo",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-spider fa-lg condition-main-color"></span>
                </span>
            """,
        },
        {
            'category': 'in_house',
            'name_en': "Small children",
            'name': "Malgrandaj infanoj hejme",
            'restriction': True,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-baby fa-lg condition-main-color"></span>
                </span>
            """,
        },
        {
            'category': 'in_house',
            'name_en': "Suitable for babies/toddlers",
            'name': "Taŭga por beboj/infanetoj",
            'restriction': False,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-shield-blank condition-main-color" style="font-size: 1.5em; top: -0.07em"></span>
                    <span class="fa fa-stack-1x fa-child" style="color: #fff; top: -0.1em"></span>
                </span>
            """,
        },
        {
            'category': 'outside_house',
            'name_en': "Accessible for wheelchair",
            'name': "Alirebla por rulseĝoj",
            'restriction': False,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-wheelchair fa-lg condition-main-color"></span>
                </span>
            """,
        },
        {
            'category': 'outside_house',
            'name_en': "Accessible by elevator or without it",
            'name': "Atingebla sen aŭ per lifto",
            'restriction': False,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-elevator fa-lg condition-main-color" style="top: -0.1em"></span>
                </span>
            """,
        },
        {
            'category': 'outside_house',
            'name_en': "Space for a camper",
            'name': "Loko por loĝaŭto",
            'restriction': False,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-1x fa-caravan fa-lg centered-horizontally condition-main-color"></span>
                </span>
            """,
        },
        {
            'category': 'outside_house',
            'name_en': "Safe parking for a bicycle",
            'name': "Sekura parkloko por biciklo",
            'restriction': False,
            'icon': """
                <span class="fa-stack" aria-hidden="true">
                    <span class="fa fa-stack-2x fa-regular fa-square condition-main-color"></span>
                    <span class="fa fa-stack-1x fa-bicycle condition-main-color"></span>
                </span>
            """,
        },
    )
    Condition.objects.bulk_create(
        [Condition(**data_dict) for data_dict in data]
    )
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), [Condition]):
            cursor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('hosting', '0065_enable_psql_ext_unaccent'),
    ]

    operations = [
        migrations.AddField(
            model_name='condition',
            name='category',
            field=models.CharField(choices=[('in_house', 'in the house'), ('sleeping_cond', 'sleeping conditions'), ('outside_house', 'outside the house')], default='sleeping_cond', max_length=15, verbose_name='category'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='condition',
            name='name_en',
            field=models.CharField(default='-', help_text="E.g.: 'Don't smoke'.", max_length=255, verbose_name='name (in English)'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='condition',
            name='icon',
            field=models.TextField(default='<span class="fa-stack"></span>', verbose_name='icon'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='condition',
            name='abbr',
            field=models.CharField(blank=True, help_text="Official abbreviation as used in the book. E.g.: 'Nef.'", max_length=20, verbose_name='abbreviation'),
        ),
        migrations.AddField(
            model_name='condition',
            name='restriction',
            field=models.BooleanField(default=True, help_text='Marked = restriction for the guests, unmarked = facilitation for the guests.', verbose_name='is a limitation'),
        ),

        migrations.RunPython(update_existing_conditions, revert_existing_conditions),

        migrations.RemoveField(
            model_name='condition',
            name='slug',
        ),

        migrations.RunPython(add_new_conditions, migrations.RunPython.noop),
    ]
