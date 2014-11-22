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
        SELECT u.uid id,
            field_nomo_kaj_familia_nomo_1_value name1,
            field_naskijaro_persono_1_value year1,
            field_sekso_persono_1_value sex1,
            field_nomo_kaj_familia_nomo_2_value name2,
            field_naskijaro_persono_2_value year2,
            field_sekso_persono_1_value sex2,
            field_nomo_kaj_familia_nomo_3_value name3,
            field_naskijaro_persono_3_value year3
            -- There is no field_sekso_persono_3_value in the source database
        FROM users u
        INNER JOIN node n ON n.uid=u.uid AND n.type='profilo'
        INNER JOIN content_type_profilo p ON p.nid=n.nid
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
    from hosting.models import Profile, Place

    django.setup()

    # Starting...
    print('Ignoring:')


    while user is not None:

        data1 = {'first_name': title_with_particule(user['name1']), 'birth_date': g.get_birth_date(user['year1']), 'title': g.get_title(user['sex1'])}
        data2 = {'first_name': title_with_particule(user['name2']), 'birth_date': g.get_birth_date(user['year2']), 'title': g.get_title(user['sex2'])}
        data3 = {'first_name': title_with_particule(user['name3']), 'birth_date': g.get_birth_date(user['year3'])}

        try:
            place = Place.objects.get(pk=user['id'])
        except Place.DoesNotExist:
            place = None

        print(user['id'], data1['first_name'], data3['birth_date'])

        if place and (data1['birth_date'] or data1['first_name']):
            profile1 = Profile(**data1)
            profile1.save()
            place.family_members.add(profile1)

        if place and (data2['birth_date'] or data2['first_name']):
            profile2 = Profile(**data2)
            profile2.save()
            place.family_members.add(profile2)

        if place and (data3['birth_date'] or data3['first_name']):
            profile3 = Profile(**data3)
            profile3.save()
            place.family_members.add(profile3)

        user = users.fetchone()

    users.close()
    dr.close()

    print('\n  Success! \\o/\n')


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

