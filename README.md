# ![Pasporta Servo 3](https://cdn.rawgit.com/tejo-esperanto/pasportaservo/master/logos/pasportaservo_logo.svg)

[![TEJO](https://img.shields.io/badge/Projekto_de-TEJO-orange.svg)](http://tejo.org)
[![Esperanto](https://img.shields.io/badge/Esperanto-jes-green.svg)](https://eo.wikipedia.org/wiki/Esperanto)
[![Python 3.4](https://img.shields.io/badge/Python-3.4-blue.svg)](https://docs.python.org/3.4/)
[![Django 1.10](https://img.shields.io/badge/Django-1.10-0C4B33.svg)](https://docs.djangoproject.com/en/1.10/)
[![HTTP](https://img.shields.io/badge/HTTP-2-blue.svg)](https://http2.github.io/)
[![HTTPS](https://img.shields.io/badge/HTTPS-jes-green.svg)](https://letsencrypt.org/)
[![GNU AGPLv3](https://img.shields.io/badge/licenco-GNU_AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Kontaktu nin en Gitter https://gitter.im/tejo-esperanto/pasportaservo](https://img.shields.io/gitter/room/tejo-esperanto/pasportaservo.svg)](https://gitter.im/tejo-esperanto/pasportaservo?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Twitter URL](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](https://twitter.com/pasportaservo)

[Pasporta Servo](https://eo.wikipedia.org/wiki/Pasporta_Servo) estas senpaga tutmonda gastiga servo. La projekto komencis en 1974 kiel eta jarlibro, kaj ekde 2009 ankaŭ daŭras kiel retejo. En tiu ĉi deponejo kolektiĝas la kodo kiu ruligas la retejon [pasportaservo.org](https://pasportaservo.org).


- [Kontribui](#kontribui)
- [Instali](#instali)
- [Licenco](#licenco)

## Kontribui

Ĉu vi trovis cimon? Ĉu vi havas ideo kiel plibonigi la retejon? Nepre kreu [novan atentindaĵon](https://github.com/tejo-esperanto/pasportaservo/issues/new).

Ĉu vi konas Pitonon kaj Dĵangon, aŭ volas lerni, legu [kiel instali](INSTALL.md).

Ĉiu kaze estas bona ideo veni sur [la Gitter babilejon](https://gitter.im/tejo-esperanto/pasportaservo) kaj legi kiel esti [pli bona kontribuanto](CONTRIBUTING.md).


## Instali

```bash
$ mkvirtualenv ps -p python3
(ps) $ git clone https://github.com/tejo-esperanto/pasportaservo.git
(ps) $ cd pasportaservo
(ps) $ pip install -r requirements.txt
(ps) $ ./manage.py migrate
(ps) $ ./manage.py runserver
```

Pli detale: [INSTALL.md](INSTALL.md)


## Licenco

[GNU AGPLv3](LICENSE)
