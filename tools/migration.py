#!/usr/bin/env python

import psycopg2 as pg
import pymysql as mdb
from datetime import datetime
import hashlib

import pprint

def u2dt(timestamp):
    """A convenience function to easily convert unix timestamps to datetime strings."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Connect to an existing database
dr = mdb.connect('localhost', 'pasportaservo', 'pasportaservo', 'pasportaservo')
dj = pg.connect("dbname=pasportaservo user=guillaume")

# First of all, users.
users = dr.cursor(mdb.cursors.DictCursor)
users.execute("""
    SELECT *
    FROM users u
    INNER JOIN node n ON n.uid=u.uid AND n.type='profilo'
    INNER JOIN content_type_profilo p ON p.nid=n.nid
    WHERE u.uid > 1
    GROUP BY u.uid
""")

user = users.fetchone()
newuser = dj.cursor()
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
    try:
        newuser.execute("""
            INSERT INTO
            auth_user(
                id,
                password,
                last_login,
                is_superuser,
                username,
                first_name,
                last_name,
                email,
                is_staff,
                is_active,
                date_joined
            )
            VALUES(
                %s, %s, %s, 'f', %s, %s, %s, %s, 'f', 't', %s
            )""",
            (user['uid'], user['pass'], u2dt(user['login']), username, user['field_persona_nomo_value'],
            user['field_familia_nomo_value'], user['mail'], u2dt(user['created'])))
    except pg.DataError as e:
        print("Insert error for user {0}".format(user['uid']))
        print(e)
        pprint.pprint(user)
        # Cleanup
        dj.rollback()
        newuser.close()
        users.close()
        dr.close()
        exit()
    user = users.fetchone()

dj.commit()
newuser.close()
users.close()
dr.close()

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
