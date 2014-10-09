#!/usr/bin/env python
import os, sys
import pprint
import pytz
import pymysql as mdb
import hashlib
from datetime import datetime

import django
from django.utils.timezone import make_aware
from django.db import transaction

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'pasportaservo.settings'


def u2dt(timestamp):
    """A convenience function to easily convert unix timestamps to datetime strings."""
    # return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return make_aware(datetime.fromtimestamp(timestamp), pytz.timezone('UTC'))


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
        newuser = User(
                id=user['uid'],
                password="md5$1$${0}".format(user['pass']),
                last_login=u2dt(user['login']),
                is_superuser=False,
                username=username,
                first_name=user['field_persona_nomo_value'],
                last_name=user['field_familia_nomo_value'],
                email=user['mail'],
                is_staff=False,
                is_active=True,
                date_joined=u2dt(user['created'])
            )
        newuser.save()
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

