#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
import pprint
import pytz
import pymysql as mdb
from datetime import datetime
from getpass import getpass

import django
from django.utils.timezone import make_aware
from django.utils.translation import ugettext_lazy as _
from django.db import transaction

from countries import COUNTRIES, PHONE_CODES
import getters as g


PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'pasportaservo.settings'


def u2dt(timestamp):
    """A convenience function to easily convert unix timestamps to datetime TZ aware."""
    return make_aware(datetime.fromtimestamp(timestamp), pytz.timezone('UTC'))

@transaction.atomic
def migrate():
    # Connect to an existing database
    passwd = getpass("MySQL password for 'root': ")
    dr = mdb.connect('localhost', 'root', passwd, 'pasportaservo', charset='utf8')

    users = dr.cursor(mdb.cursors.DictCursor)
    users.execute("""
        SELECT *,
            GROUP_CONCAT(DISTINCT content_field_kondicxoj.field_kondicxoj_value) conditions,
            GROUP_CONCAT(DISTINCT content_field_telefono1estas.field_telefono1estas_value) tel1_type,
            GROUP_CONCAT(DISTINCT content_field_telefono2estas.field_telefono2estas_value) tel2_type
        FROM users u
        INNER JOIN node n ON n.uid=u.uid AND n.type='profilo'
        INNER JOIN content_type_profilo p ON p.nid=n.nid
        LEFT JOIN location_instance
            ON u.uid = location_instance.uid
        LEFT JOIN location
            ON location_instance.lid = location.lid
        LEFT JOIN content_field_kondicxoj
            ON n.nid = content_field_kondicxoj.nid
        LEFT JOIN content_field_telefono1estas
            ON n.nid = content_field_telefono1estas.nid
        LEFT JOIN content_field_telefono2estas
            ON n.nid = content_field_telefono2estas.nid
        WHERE u.uid > 1
            AND u.name <> 'testuser'
            AND ( (field_lando_value = 'Albanio' AND field_urbo_value is not NULL)
                OR (field_lando_value <> 'Albanio'))
            AND field_familia_nomo_value <> 12
        GROUP BY u.uid
    """)

    user = users.fetchone()

    from django.contrib.auth.models import User
    from hosting.utils import title_with_particule
    from hosting.models import Profile, Place, Phone, Condition

    django.setup()

    # Starting...
    print('Ignoring:')

    # Condition objects
    sleeping_bag = Condition(
            name=_("Sleeping bag"),
            abbr=_("sleeping bag"),
            slug="sleeping-bag",
    )
    sleeping_bag.save()

    one_room = Condition(
            name=_("One room"),
            abbr=_("one room"),
            slug="one-room",
    )
    one_room.save()

    dont_smoke = Condition(
            name=_("Don't smoke"),
            abbr=_("dont smoke"),
            slug="dont-smoke",
    )
    dont_smoke.save()


    while user is not None:

        # User
        new_user = User(
                id=user['uid'],
                password=user['pass'],
                last_login=u2dt(user['login']),
                is_superuser=False,
                username=g.get_username(user['name'], user['mail']),
                email=user['mail'],
                is_staff=False,
                is_active=True,
                date_joined=u2dt(user['created'])
            )
        new_user.save()

        # Profile
        new_profile = Profile(
                id=user['uid'],
                user=new_user,
                title=g.get_title(user['field_sekso_value']),
                first_name=title_with_particule(user['field_persona_nomo_value']),
                last_name=title_with_particule(user['field_familia_nomo_value']),
                birth_date=g.get_birth_date(user['field_naskijaro_value']),
                description=user['field_pri_mi_value'],
                avatar=g.get_avatar(user['picture']),
        )
        new_profile.save()

        # Place
        address = user['field_adreso_value']
        details = user['field_detaloj_kaj_rimarkoj_value']
        closest_city = user['field_proksima_granda_urbo_value']
        city = user['field_urbo_value']
        country = COUNTRIES.get(user['field_lando_value'], '')
        state_province = g.get_state_province(user['field_sxtato_provinco_value'], country)
        if address or user['latitude']:
            new_place = Place(
                    id=user['uid'],
                    address='' if not address else address.strip(),
                    description='' if not details else details.strip(),
                    city='' if not city else title_with_particule(city.strip()),
                    closest_city='' if not closest_city else title_with_particule(closest_city.strip()),
                    postcode=g.get_postcode(user['field_posxtokodo_logxadreso_value']),
                    country=country,
                    state_province=state_province,
                    latitude=None if not user['latitude'] else float(user['latitude']),
                    longitude=None if not user['longitude'] else float(user['longitude']),
                    max_host=g.get_int_or_none(user['field_maksimuma_gastoj_value']),
                    max_night=g.get_int_or_none(user['field_maksimuma_noktoj_value']),
                    available=g.get_truefalse(user['field_mi_pretas_gastigi_value']),
                    tour_guide=g.get_truefalse(user['field_mi_pretas_cxicxeroni_value']),
                    have_a_drink=g.get_truefalse(user['field_mi_pretas_cxicxeroni_value']),
                    in_book=g.get_in_book(user['field_mia_profilo_videbla_en_la_value']),
                    contact_before=g.get_int_or_none(user['field_bonvolu_kontakti_min_value']),
            )
            new_place.save()
            new_profile.places.add(new_place)

            # Conditions
            raw_conditions = user['conditions']
            if raw_conditions:
                if "Kunportu dormosakon" in raw_conditions:
                    new_place.conditions.add(sleeping_bag)
                if "Ne fumu" in raw_conditions:
                    new_place.conditions.add(dont_smoke)
                if "ambra lo" in raw_conditions:
                    new_place.conditions.add(one_room)

        # Phone number
        raw_number = user['field_telefono1_value']
        number = g.get_phone_number(raw_number, country) if raw_number else ''
        if number:
            new_number = Phone(
                    number=number,
                    country=country if country else PHONE_CODES.get(number.country_code, ''),
                    type=g.get_phone_type(user['tel1_type']),
            )
            new_number.save()
            new_profile.phones.add(new_number)

        # Phone number 2
        raw_number2 = user['field_telefono2_value']
        number2 = g.get_phone_number(raw_number2, country) if raw_number2 else ''
        if number2:
            new_number2 = Phone(
                    number=number2,
                    country=country if country else PHONE_CODES.get(number2.country_code, ''),
                    type=g.get_phone_type(user['tel2_type']),
            )
            new_number2.save()
            new_profile.phones.add(new_number2)

        user = users.fetchone()

    users.close()
    dr.close()

    print(r'Success! \o/')


if __name__ == '__main__':
    migrate()


# Open a cursor to perform database operations
#cur = dj.cursor()

# Execute a command: this creates a new table
#cur.execute("CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);")

# Pass data to fill a query placeholders and let Psycopg perform
# the correct conversion (no more SQL injections!)
#cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))

# Query the database and obtain data as Python objects
#cur.execute("SELECT * FROM test;")
#cur.fetchone()

# Make the changes to the database persistent
#conn.commit()

# Close communication with the database
#cur.close()
#conn.close()

