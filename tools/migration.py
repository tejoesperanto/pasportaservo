#!/usr/bin/env python
import os, sys
import re
import pprint
import pytz
import pymysql as mdb
import hashlib
from datetime import datetime, date

import django
from django.utils.timezone import make_aware
from django.db import transaction

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'pasportaservo.settings'


def u2dt(timestamp):
    """A convenience function to easily convert unix timestamps to datetime TZ aware."""
    return make_aware(datetime.fromtimestamp(timestamp), pytz.timezone('UTC'))

def get_title(sekso):
    if sekso == 'Ina':
        return 'Mrs'
    if sekso == 'Vira':
        return 'Mr'
    return ''


def get_birth_date(year):
    if year:
        year = year.strip(' .-')
        if len(year) == 4:
            return date(int(year), 1, 1)
        if len(year) == 2 and int(year) > 30:
            return date(int('19'+year), 1, 1)
        if '/' in year:
            day, month, y = year.split('/')
            if len(y) == 2:
                return date(int('19'+y), int(month), int(day))
            elif len(y) == 4:
                return date(int(y), int(month), int(day))
        else:
            print('Non valid year:', year)
    return None


@transaction.atomic
def migrate():
    # Connect to an existing database
    dr = mdb.connect('localhost', 'root', 'blfpd', 'pasportaservo')

    # First of all, users.
    users = dr.cursor(mdb.cursors.DictCursor)
    users.execute("""
        SELECT *
        FROM users u
        INNER JOIN node n ON n.uid=u.uid AND n.type='profilo'
        INNER JOIN content_type_profilo p ON p.nid=n.nid
        WHERE u.uid > 1
            AND ( (field_lando_value = 'Albanio' AND field_urbo_value is not NULL)
                OR (field_lando_value <> 'Albanio'))
        GROUP BY u.uid
    """)

    user = users.fetchone()

    from django.contrib.auth.models import User
    from hosting.models import Profile
    django.setup()

    while user is not None:
        username = user['name'].strip()
        if len(username) > 30:
            if len(user['mail']) > 30:
                username = user['mail'][0:user['mail'].index('@')]
                if len(username) > 30:
                    h = hashlib.md5()
                    h.update(username)
                    username = h.digest()
            else:
                username = user['mail']
        new_user = User(
                id=user['uid'],
                password=user['pass'],
                last_login=u2dt(user['login']),
                is_superuser=False,
                username=username,
                email=user['mail'],
                is_staff=False,
                is_active=True,
                date_joined=u2dt(user['created'])
            )
        new_user.save()

        new_profile = Profile(
                user=new_user,
                title=get_title(user['field_sekso_value']),
                first_name=user['field_persona_nomo_value'],
                last_name=user['field_familia_nomo_value'],
                birth_date=get_birth_date(user['field_naskijaro_value']),
                description=user['field_pri_mi_value'],
        )
        new_profile.save()

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

