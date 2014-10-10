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
from django.db import transaction

from countries import COUNTRIES
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

    # First of all, users.
    users = dr.cursor(mdb.cursors.DictCursor)
    users.execute("""
        SELECT *
        FROM users u
        INNER JOIN node n ON n.uid=u.uid AND n.type='profilo'
        INNER JOIN content_type_profilo p ON p.nid=n.nid
        LEFT JOIN location_instance
            ON u.uid = location_instance.uid
        LEFT JOIN location
            ON location_instance.lid = location.lid
        WHERE u.uid > 1
            AND ( (field_lando_value = 'Albanio' AND field_urbo_value is not NULL)
                OR (field_lando_value <> 'Albanio'))
            AND field_familia_nomo_value <> 12
        GROUP BY u.uid
    """)

    user = users.fetchone()

    from django.contrib.auth.models import User
    from hosting.utils import title_with_particule
    from hosting.models import Profile, Place
    django.setup()

    while user is not None:
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

        address = user['field_adreso_value']
        if address is not None and address.strip():
            new_place = Place(
                    address=address.strip(),
                    description=user['field_detaloj_kaj_rimarkoj_value'].strip(),
                    city=title_with_particule(user['field_urbo_value'].strip()),
                    closest_city=title_with_particule(user['field_proksima_granda_urbo_value'].strip()),
                    postcode=g.get_postcode(user['field_posxtokodo_logxadreso_value']),
                    country=COUNTRIES.get(user['field_lando_value']),
                    latitude = user['latitude'],
                    longitude = user['longitude'],
            )
            new_place.save()
            new_profile.places.add(new_place)

        user = users.fetchone()

    users.close()
    dr.close()


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

