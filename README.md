# ![Pasporta Servo 3](https://cdn.rawgit.com/tejo-esperanto/pasportaservo/master/logos/pasportaservo_logo.svg)

[![TEJO](https://img.shields.io/badge/Projekto_de-TEJO-orange.svg)](https://tejo.org)
[![Esperanto](https://img.shields.io/badge/Esperanto-jes-green.svg)](https://eo.wikipedia.org/wiki/Esperanto)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-blue.svg)](https://docs.python.org/3.10/)
[![Django 3.2](https://img.shields.io/badge/Django-3.2-0C4B33.svg)](https://docs.djangoproject.com/en/3.2/)
[![HTTP](https://img.shields.io/badge/HTTP-2-blue.svg)](https://http2.github.io/)
[![HTTPS](https://img.shields.io/badge/HTTPS-jes-green.svg)](https://www.ssllabs.com/ssltest/analyze.html?d=pasportaservo.org)
[![GNU AGPLv3](https://img.shields.io/badge/licenco-GNU_AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Kontaktu nin en Telegramo https://t.me/joinchat/Bg10skEz3jFXpBk-nZAuiw](https://img.shields.io/badge/babili%20en-Telegramo-179CDE.svg)](https://t.me/joinchat/Bg10skEz3jFXpBk-nZAuiw)

![CI build](https://github.com/tejoesperanto/pasportaservo/actions/workflows/ci.yml/badge.svg)
[![Codecov](https://img.shields.io/codecov/c/github/tejoesperanto/pasportaservo.svg)](https://codecov.io/github/tejoesperanto/pasportaservo)


### [Pasporta Servo](https://eo.wikipedia.org/wiki/Pasporta_Servo) estas senpaga tutmonda gastiga servo.

**La projekto komenciĝis en 1974 kiel eta jarlibro, kaj ekde 2009 daŭras ankaŭ kiel retejo
  (unue surbaze de Drupalo kaj nuntempe sur [Dĵango](https://www.djangoproject.com)).
  En tiu ĉi deponejo kolektiĝas la kodo kiu ruligas la retejon [pasportaservo.org](https://www.pasportaservo.org).**

- [Kontribui](#kontribui)
- [Instali](#instali)
- [Kunlabori](#kunlabori)
- [Licenco](#licenco)


# Kontribui

Ĉu vi trovis cimon? Nepre kreu [novan atentindaĵon](https://github.com/tejoesperanto/pasportaservo/issues/new).

Ĉu vi havas ideon kiel plibonigi la retejon?
Kontrolu ĉe [Diskutoj](https://github.com/tejoesperanto/pasportaservo/discussions) ĉu iu jam eble proponis ion
similan – se jes, voĉdonu por tiu ideo;
se ne, komencu [novan fadenon](https://github.com/tejoesperanto/pasportaservo/discussions/new?category=ideas).


# Instali

Ubuntu 16.10 / Debian Stretch:

    sudo apt install git python3-dev python3-pip python3-venv libjpeg-dev zlib1g-dev \
      postgresql-contrib postgresql-server-dev-all postgresql-10-postgis libgdal-dev gcc-c++ gdal

Fedora 27:

    sudo dnf install git python3-devel python3-crypto redhat-rpm-config zlib-devel libjpeg-devel libzip-devel \
      postgresql-server postgresql-contrib postgresql-devel gcc-c++ gdal


#### PostgreSQL

Se vi estas sub Fedora:

    sudo postgresql-setup --initdb --unit postgresql
    sudo systemctl enable postgresql
    sudo systemctl start postgresql

Por ĉiuj:

    sudo -u postgres createuser --interactive  # Enigu vian uzantnomon kaj poste 'y'
    createdb via-uzantnomo
    createdb pasportaservo


#### Fontkodo

Iru al la [projektpaĝo ĉe GitHub](https://github.com/tejoesperanto/pasportaservo)
kaj forku la deponejon. Poste, vi povas kloni ĝin:

    git clone https://github.com/{via-uzantnomo}/pasportaservo.git

Instalu ĉiujn necesajn pakaĵojn kaj pretigu la datumbazon (ne forgesu tion fari ene de virtuala medio):

    cd pasportaservo
    pip install wheel
    pip install -r requirements/dev.txt
    echo 'from .dev import *' > pasportaservo/settings/__init__.py
    ./manage.py migrate
    ./manage.py createsuperuser  # Nur la uzantnomo kaj pasvorto estas deviga

Fine, kurigu la lokan WSGI-servilon:

    ./manage.py runserver

Ĉu bone? Vidu http://localhost:8000.


#### Retmesaĝoj

Dum disvolvigo, estas praktika uzi *MailDump* por provadi sendi retmesaĝojn.
Ekster la *env* virtuala medio, kun Pitono:

    pip install --user maildump
    maildump

La mesaĝoj estos kolektataj en ĉion-kaptan poŝtkeston videblan ĉe http://localhost:1080.


----


### Problem-solvado

#### PostgreSQL: `unrecognized option --interactive`
Se la komando `sudo -u postgres createuser --interactive` malsukcesas
(ekz., vi ricevas eraron "unrecognized option --interactive"), provu:

    $ sudo -u postgres psql
    psql (9.6.6)
    Type "help" for help.
    postgres=# CREATE ROLE {via-uzantonomo} WITH LOGIN CREATEDB CREATEROLE;
    postgres=# \q

#### PostgreSQL: Ĉu mi bone kreis la datumbazojn?

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

#### Lokaĵaro: `Could not set locale eo.UTF-8: make sure that it is enabled on the system`
Tia eraro indikas ke la Esperanta lokaĵaro ne estas aktivigita. Uzu la jenajn komandojn:

    sudo locale-gen eo.UTF-8
    sudo update-locale
    locale -a

Se vi vidas `eo.utf8` en la listo, la ĝusta lokaĵaro estas nun aktiva.


# Kunlabori

### Komprenu la strukturon de la kodo

- **pasportaservo/**: ĝenerala dosierujo kun konfiguro, baz-nivelaj URL-oj, bibliotekoj, ktp
- **core/**: bazaj ŝablonoj kaj ĉio rilata al aŭtentigo kaj (rolbazita) rajtigado
- **hosting/**: la ĉefa programo por gastiga servo

Kaj ene de la diversaj *Dĵango-aplikaĵoj* (ekz. `hosting`, `pages`, `links`…):

- models.py: strukturo de la datumoj, kaj bazaj operacioj por ĉiu modelo
- forms.py: formularoj por enigi kaj modifi datumojn
- urls.py: ligoj inter URL-oj kaj paĝo-vidoj
- views.py: difino de vidoj, paĝoj por prezentado
- templates/: pseŭdo-HTML dosieroj (ŝablonoj)
- templatetags/: ebligas pli kompleksajn operaciojn en la ŝablonoj


### Disvolvigu

*Laboru en branĉoj:*

Efektivigu viajn ŝanĝojn en tiucelaj, laŭtemaj branĉoj:

    git checkout master
    git checkout -b {nomo-de-nova-branĉo}

Ĉefa risurco por lerni ***git*** (la versiadministra sistemo): https://git-scm.com/docs/git.

*Utiligu helpilojn por kod-kvalito:*

* *isort* aŭtomate ordigas ĉiujn importojn en la Pitonaj dosieroj, por ke vi ne devu pensi pri tio
  (`isort -rc .`)
* *flake8* certigas ke la kodo estas bonkvalite strukturita kaj ne ĉeestas “mortaj” sekcioj
  (`python -m flake8`)

*Verku testojn:*

Testoj estas gravaj por certigi ke partoj de la retejo funkcias tiele kiel oni planis, kaj kapti cimojn
antaŭ ol ili trafos uzantojn. Testoj ankaŭ helpas certiĝi ke novenkondukitaj ŝanĝoj ne rompas ekzistantajn
funkciojn. La testoj kolektiĝas sub **tests/**. Risurcoj:
- https://docs.djangoproject.com/en/stable/topics/testing/overview
- https://docs.python.org/3/library/unittest.html
- https://docs.pylonsproject.org/projects/webtest/en/latest
- https://test-driven-django-development.readthedocs.io/en/latest

*Testu sur realaj aparatoj:*

Laŭdefaŭlte, la disvolviga WSGI-servilo estas kurigita izolite sur via maŝino kaj atingeblas nur per la
loka inverscikla adreso 127.0.0.1 (aŭ ĝia sinonimo http://localhost). Tiam vi povas uzi la retumilojn
haveblajn sur via maŝino por testadi la retejon. Tamen, Dĵango efektive subtenas kurigon sur ajna reta
interfaco; uzante la komandon

    python ./manage.py runserver {IP-adreso-en-loka-reto}:8000

vi povas videbligi la retejon ene de via loka reto (LAN / Wifi) kaj aliri ĝin per ajna aparato konektita
al la sama reto. Tiamaniere vi povas testi la ĝustan funkciadon de la retejo sur pli diversaj aparatoj
(ekz., ankaŭ per poŝtelefonoj).
Tion ebligas agordo *settings/dev.py/*`ALLOWED_HOSTS` – dum lanĉo, la servilo provas eltrovi la lokaretan
IP-adreson de la maŝino kaj permesi ties uzon.


### Lernu Dĵangon

- https://tutorial.djangogirls.org/
- https://docs.djangoproject.com/en/stable/intro/tutorial01/
- https://docs.djangoproject.com/en/stable/


# Licenco

[GNU AGPLv3](LICENSE)
