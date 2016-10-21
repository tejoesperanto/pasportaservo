# INSTALI

Tiu ĉi projekto uzas Dĵangon 1.10; vidu requirements.txt.

Vi bezonos Pitonon 3.4+, PostgreSQL, PIP kaj Virtualenv :

    $ sudo apt-get install postgresql postgresql-client postgresql-client-common libpq5 libpq-dev
    $ sudo apt-get install python3 python3-dev
    $ sudo apt-get install mercurial
    $ sudo apt-get install python-setuptools
    $ easy_install --user pip
    $ sudo pip install virtualenv

Kiam eblas, ne instalu Django-n en via ĉefa sistemo sed ene de virtualenv, kiu provizas hermetikan Python-ĉirkaŭaĵon. Tiukaze, se vi provos lanĉi Django-n ekster la agordita ĉirkaŭaĵo, okazos eraro.

    $ virtualenv {ENV}
    $ source ./{ENV}/bin/activate

Kie `{ENV}` (ekz, 'PS3') estas la dosierujo enhavonta ĉion necesan por la ĉirkaŭaĵo, inkluzive de Python kaj bibliotekoj. `deactivate` por eliri el la ĉirkaŭaĵo.

#### Konfiguro de PostgreSQL

    $ sudo -u postgres createuser {via-uzantonomo} --interactive

Kie `{via-uzantonomo}` estas de tiu uzanto per kiu vi aktuale estas ensalutinta. Respondu:

>    Shall the new role be a superuser? (y/n) **n**
>
>    Shall the new role be allowed to create databases? (y/n) **y**
>
>    Shall the new role be allowed to create more new roles? (y/n) **n**

Se la antaŭa komando malsukcesas (ekz., vi ricevas eraron "unrecognized option --interactive"), provu:

    $ sudo -u postgres psql
    psql (9.4.9)
    Type "help" for help.
    postgres=# CREATE ROLE {via-uzantonomo} WITH LOGIN CREATEDB CREATEROLE;
    postgres=# \q

Sekvas kreo de datumbazo.

    $ sudo -u postgres createdb -O {via-uzantonomo} -E utf8 pasportaservo
    $ sudo -u postgres psql
    psql (9.4.9)
    Type "help" for help.
    postgres=# \l
                                        List of databases
         Name      |  Owner   | Encoding |   Collate   |    Ctype    |   Access privileges   
    ---------------+----------+----------+-------------+-------------+-----------------------
     pasportaservo | {uzanto} | UTF8     | en_US.UTF-8 | en_US.UTF-8 | 
     template0     | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =c/postgres          +
                   |          |          |             |             | postgres=CTc/postgres
     template1     | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =c/postgres          +
                   |          |          |             |             | postgres=CTc/postgres

    postgres=# \q

Se vi vidas tabelon kiel ĉi-supre, ĉio glate paŝis.

#### Elpreno de kodo kaj lanĉo

    (PS3) $ mkdir site
    (PS3) $ cd site/
    (PS3) $ git clone https://github.com/tejo-esperanto/pasportaservo.git
    (PS3) $ cd pasportaservo
    (PS3) $ pip install -r requirements.txt  # aŭ requirements/dev.txt
    (PS3) $ cd pasportaservo/settings/
    (PS3) $ ln -s {my-local-settings}.py local_settings.py
    (PS3) $ cd -

> `my-local-settings.py` povas esti `dev.py`, `staging.py` aŭ `prod.py`

    (PS3) $ ./manage.py migrate
    (PS3) $ ./manage.py runserver

En la krozilo, iru al la adreso `http://127.0.0.1:8000`.


## Komprenu la strukturon de la kodo

- **pasportaservo/**: ĝenerala dosierujo kun konfiguro, baz-nivelaj URL-oj…
- **hosting/**: la ĉefa programo por gastiganta servo

**Gravaj dosieroj por Gastigoservo:**

- models.py: strukturo de la datumoj
- urls.py: ligoj inter URL-oj kaj paĝo-vidoj
- views.py: difino de vidoj, paĝoj por prezentado
- templates/: pseŭdo-HTML dosieroj (ŝablonoj)
