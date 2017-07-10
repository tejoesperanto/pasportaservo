# INSTALI

Ubuntu 16.10 / Debian 9 Stretch:

    sudo apt install git python3-dev python3-pip libjpeg-dev zlib1g-dev \
      postgresql-contrib postgresql-server-dev-all postgresql-9.6-postgis

Fedora 26:

    sudo dnf install git python3-devel python3-crypto redhat-rpm-config zlib-devel libjpeg-devel libzip-devel \
      postgresql-server postgresql-contrib postgresql-devel


#### PostgreSQL

Se vi estas sub Fedora:

    sudo postgresql-setup --initdb --unit postgresql
    sudo systemctl enable postgresql
    sudo systemctl start postgresql

Por ĉiuj:

    sudo -u postgres createuser --interactive  # Enigu vian uzantnomon kaj poste 'y'
    createdb via-uzantnomo
    createdb pasportaservo


#### VirtualenvWrapper

Uzi virtualenvwrapper ne estas deviga, Pitono 3 venas kun `venv`.
Tamen tiu ilo estas praktika kaj uzata sur la servilo.

    sudo pip3 install virtualenvwrapper

Aldonu tion al la fino de via `.bashrc`, `.bash_profile` aŭ simile:

    # VirtualenvWrapper
    export WORKON_HOME=/opt/envs/
    export VIRTUALENVWRAPPER_PYTHON=`which python3`
    source `which virtualenvwrapper.sh`

Kaj poste kreu dosierujon por la virtualaj medioj:

    sudo mkdir /opt/envs && sudo chown uzantnomo:uzantnomo /opt/envs
    source .bashrc
    mkvirtualenv ps
    python -V  # Ĉu Python 3.5?


#### Fontkodo

Iru al la [Github projektpaĝo](https://github.com/tejo-esperanto/pasportaservo)
kaj forku ĝin. Poste, vi povas kloni ĝin:

    git clone https://github.com/via-uzantnomo/pasportaservo.git
    cd pasportaservo
    git checkout devel
    pip install -r requirements/dev.txt
    echo 'from .dev import *' > pasportaservo/settings/__init__.py
    ./manage.py migrate
    ./manage.py createsuperuser
    ./manage.py runserver

Ĉu bone? Vidu http://localhost:8000

----


#### Retmesaĝoj

Dum disvolvigo, estas praktika uzi *MailDump* por provadi sendi retmesaĝoj:

    pip install maildump
    maildump


## Problem-solvado

#### PostgreSQL: `unrecognized option --interactive`
Se la komando `sudo -u postgres createuser --interactive` malsukcesas (ekz., vi ricevas eraron "unrecognized option --interactive"), provu:

    $ sudo -u postgres psql
    psql (9.5.4)
    Type "help" for help.
    postgres=# CREATE ROLE {via-uzantonomo} WITH LOGIN CREATEDB CREATEROLE;
    postgres=# \q

#### PostgreSQL: Ĉu mi bone kreis la datumbazoj?

    $ sudo -u postgres psql
    psql (9.5.4)
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


## Komprenu la strukturon de la kodo

- **pasportaservo/**: ĝenerala dosierujo kun konfiguro, baz-nivelaj URL-oj…
- **hosting/**: la ĉefa programo por gastiganta servo

Kaj en la diversaj *aplikaĵon* (ekz. `hosting`, `book`, `links`…):

- models.py: strukturo de la datumoj
- urls.py: ligoj inter URL-oj kaj paĝo-vidoj
- views.py: difino de vidoj, paĝoj por prezentado
- templates/: pseŭdo-HTML dosieroj (ŝablonoj)


## Lerni Dĵangon

- https://tutorial.djangogirls.org/
- https://docs.djangoproject.com/en/stable/intro/tutorial01/
- https://docs.djangoproject.com/en/stable/
