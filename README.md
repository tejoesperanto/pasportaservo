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
- [Servi](#servi)
- [Kunlabori](#kunlabori)
- [Licenco](#licenco)


# Kontribui

Ĉu vi trovis cimon? Nepre kreu [novan atentindaĵon](https://github.com/tejoesperanto/pasportaservo/issues/new).

Ĉu vi havas ideon kiel plibonigi la retejon?
Kontrolu ĉe [Diskutoj](https://github.com/tejoesperanto/pasportaservo/discussions) ĉu iu jam eble proponis ion
similan – se jes, voĉdonu por tiu ideo;
se ne, komencu [novan fadenon](https://github.com/tejoesperanto/pasportaservo/discussions/new?category=ideas).


# Instali

## Aŭtomate

1. Iru al la projektpaĝo ĉe GitHub kaj forku la deponejon.
2. Klonu vian forkon, ekz. `git clone https://github.com/{via-uzantnomo}/pasportaservo.git`
3. Uzu la instalilon: `cd pasportaservo && ./setup.sh`

## Paŝon post paŝo

### *Sistemaj devigaĵoj*

#### Ubuntu 22.04:
```bash
sudo apt install git postgresql-server-dev-all postgresql-contrib postgis postgresql-postgis build-essential gcc libjpeg-dev zlib1g-dev libgdal-dev
```

#### Fedora 27:
```bash
sudo dnf install git python3-devel python3-crypto redhat-rpm-config zlib-devel libjpeg-devel libzip-devel postgresql-server postgresql-contrib postgresql-devel gcc-c++ gdal
```

### *PostgreSQL*

#### Se vi estas sub Fedora:
```bash
sudo postgresql-setup --initdb --unit postgresql
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

#### Por ĉiuj:
```bash
sudo -u postgres createuser --interactive  # Enigu vian uzantnomon kaj poste 'y'
createdb via-uzantnomo
createdb pasportaservo
```

### *Certiĝu, ke la Esperanta lokaĵaro haveblas*
Ĉi tiu komando indikas al vi ĉu la Esperanta lokaĵaro jam estas agordita, kaj se ne, agordas ĝin.

```bash
locale -a | grep -iq 'eo.utf8' && echo 'Lokaĵaro: En ordo' || sudo locale-gen eo.UTF-8
```

### *Fontkodo*

Iru al la [projektpaĝo ĉe GitHub](https://github.com/tejoesperanto/pasportaservo)
kaj forku la deponejon. Poste, vi povas kloni ĝin:
```bash
git clone https://github.com/{via-uzantnomo}/pasportaservo.git
```
Instalu ĉiujn necesajn pakaĵojn kaj pretigu la datumbazon (ne forgesu tion fari ene de virtuala medio):

```bash
echo 'from .dev import *' > pasportaservo/settings/__init__.py
which uv || curl -LsSf https://astral.sh/uv/0.5.1/install.sh | sh
uv venv
uv sync --all-extras
uv run ./manage.py migrate
uv run ./manage.py createsuperuser  # Nur la uzantnomo kaj pasvorto estas deviga
pre-commit install --install-hooks --overwrite
```

# Servi

Fine, kurigu la lokan WSGI-servilon:

```bash
uv run ./manage.py runserver
```

Ĉu bone? Vidu http://localhost:8000.


### Retmesaĝoj

Dum disvolvigo, estas praktika uzi *MailDump* por provadi sendi retmesaĝojn.
Ekster la virtuala medio, kun `uvx`:
```bash
uvx maildump
```
La mesaĝoj estos kolektataj en ĉion-kaptan poŝtkeston videblan ĉe http://localhost:1080.

## Problem-solvado

### PostgreSQL: `unrecognized option --interactive`
Se la komando `sudo -u postgres createuser --interactive` malsukcesas
(ekz., vi ricevas eraron "unrecognized option --interactive"), provu:

    $ sudo -u postgres psql
    psql (16.6)
    Type "help" for help.
    postgres=# CREATE ROLE {via-uzantonomo} WITH LOGIN CREATEDB CREATEROLE;
    postgres=# \q

### PostgreSQL: Ĉu mi bone kreis la datumbazojn?

    $ sudo -u postgres psql
    psql (16.6)
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

### Lokaĵaro: `Could not set locale eo.UTF-8: make sure that it is enabled on the system`
Tia eraro indikas ke la Esperanta lokaĵaro ne estas aktivigita. Uzu la jenajn komandojn:

```bash
sudo locale-gen eo.UTF-8
sudo update-locale
locale -a
```

Se vi vidas `eo.utf8` en la listo, la ĝusta lokaĵaro estas nun aktiva.

### uv: ``VIRTUAL_ENV does not match the project environment path `.venv` and will be ignored``
Se vi havas jam antaŭe agorditan virtualan medion, vi devas ligi al ĝi per `.venv` uzata fare de
`uv` tiel ke ĝi ne plendu. Ene de la virtuala medio kaj la dosierujo de la projekto:

```bash
ln -s "$VIRTUAL_ENV" .venv
```


# Kunlabori

## Komprenu la strukturon de la kodo

- `pasportaservo/`: ĝenerala dosierujo kun konfiguro, baz-nivelaj URL-oj, bibliotekoj, ktp
- `core/`: bazaj ŝablonoj kaj ĉio rilata al aŭtentigo kaj (rolbazita) rajtigado
- `hosting/`: la ĉefa programo por gastiga servo

Kaj ene de la diversaj *Dĵango-aplikaĵoj* (ekz. `hosting`, `pages`, `links`…):

- `models.py`: strukturo de la datumoj, kaj bazaj operacioj por ĉiu modelo
- `forms.py`: formularoj por enigi kaj modifi datumojn
- `urls.py`: ligoj inter URL-oj kaj paĝo-vidoj
- `views.py`: difino de vidoj, paĝoj por prezentado
- `templates/`: pseŭdo-HTML dosieroj (ŝablonoj)
- `templatetags/`: ebligas pli kompleksajn operaciojn en la ŝablonoj

## Disvolvigu

### *Laboru en branĉoj*

Efektivigu viajn ŝanĝojn en tiucelaj, laŭtemaj branĉoj:

```bash
git checkout master
git checkout -b {nomo-de-nova-branĉo}
```

Ĉefa risurco por lerni ***git*** (la versiadministra sistemo): https://git-scm.com/docs/git.

### *Utiligu helpilojn por kod-kvalito*

* ***isort*** aŭtomate ordigas ĉiujn importojn en la Pitonaj dosieroj, por ke vi ne devu pensi pri tio
  (`uvx isort .`)
* ***flake8*** certigas ke la kodo estas bonkvalite strukturita kaj ne ĉeestas “mortaj” sekcioj
  (`uvx flake8`)

### *Ŝanĝu devigajn program-partojn*

**Ne rekte ŝanĝu** iujn ajn de la `requirements/*.txt` dosieroj.
Se vi volas ŝanĝi la devigajn program-partojn, redaktu la dosieron `pyproject.toml` anstataŭe.

Vi povas rekte redakti tiun dosieron, aŭ uzi la rekomendatajn malsuprajn komandojn, kio estas pli facila.

#### Aldoni

```bash
# Aldoni al la baza grupo de pyproject.toml
# project.dependencies[...]
uv add '{aldonotaj pip-pakaĵoj}'

# Aldoni al la disvolviga grupo de pyproject.toml
# dependency-groups.dev[...]
uv add --dev '{aldonotaj pip-pakaĵoj nur al "dev"}'
```

#### Forigi

```bash
# Forigi de la baza grupo de pyproject.toml
# project.dependencies[...]
uv remove '{forigotaj pip-pakaĵoj}'

# Forigi de la disvolviga grupo de pyproject.toml
# dependency-groups.dev[...]
uv remove --dev '{forigotaj pip-pakaĵoj nur el "dev"}'
```

#### Konservi la ŝanĝojn

Post ajna ŝanĝo al `pyproject.toml`, konservu la ŝanĝojn per:
```bash
# Instali ilin kaj ŝlosi la precizajn versiojn de ili en la dosiero uv.lock
uv sync

# En ./pre-commit-commit-config.yaml, estas hokoj por elporti
# la enhavojn de `uv.lock` al la `requirements/*txt` dosieroj
# ĉar CI kaj disponigoj ankoraŭ atendas `requirements/*txt`.
uv run pre-commit run --all-files
```

### *Verku testojn*

Testoj estas gravaj por certigi ke partoj de la retejo funkcias tiele kiel oni planis, kaj kapti cimojn
antaŭ ol ili trafos uzantojn. Testoj ankaŭ helpas certiĝi ke novenkondukitaj ŝanĝoj ne rompas ekzistantajn
funkciojn. La testoj kolektiĝas sub `tests/`. Risurcoj:
- https://docs.djangoproject.com/en/stable/topics/testing/overview
- https://docs.python.org/3/library/unittest.html
- https://docs.pylonsproject.org/projects/webtest/en/latest
- https://test-driven-django-development.readthedocs.io/en/latest

### *Testu sur realaj aparatoj*

Laŭdefaŭlte, la disvolviga WSGI-servilo estas kurigita izolite sur via maŝino kaj atingeblas nur per la
loka inverscikla adreso [127.0.0.1](http://127.0.0.1) (aŭ ĝia sinonimo http://localhost). Tiam vi povas
uzi la retumilojn haveblajn sur via maŝino por testadi la retejon. Tamen, Dĵango efektive subtenas kurigon
sur ajna reta interfaco; uzante la komandon

```bash
uv run ./manage.py runserver {IP-adreso-en-loka-reto}:8000
```

vi povas videbligi la retejon ene de via loka reto (LAN / Wifi) kaj aliri ĝin per ajna aparato konektita
al la sama reto. Tiamaniere vi povas testi la ĝustan funkciadon de la retejo sur pli diversaj aparatoj
(ekz., ankaŭ per poŝtelefonoj).
Tion ebligas agordo `ALLOWED_HOSTS` de `settings/dev.py` – dum lanĉo, la servilo provas eltrovi la lokaretan
IP-adreson de la maŝino kaj permesi ties uzon.

## Lernu Dĵangon

- https://tutorial.djangogirls.org/
- https://docs.djangoproject.com/en/stable/intro/tutorial01/
- https://docs.djangoproject.com/en/stable/


# Licenco

[GNU AGPLv3](LICENSE)
