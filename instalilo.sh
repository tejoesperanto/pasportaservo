#!/usr/bin/env bash

set -e

# ĉefa
function main {
  system_package_manager
  ensure_eo_locale
  setup_postgresql
  setup_pyproject
}

function ensure_eo_locale {
  locale -a | grep -iq 'eo.utf8' && echo 'Lokaĵaro: En ordo' || sudo locale-gen eo.utf8
}

function setup_postgresql {
  set +e
  sudo postgresql-setup --initdb --unit postgresql
  sudo systemctl enable postgresql
  sudo systemctl start postgresql
  sudo -u postgres createuser -dlrs "$USER"
  createdb "$USER"
  createdb pasportaservo
  set -e
}

function setup_pyproject {
  which uv || curl -LsSf https://astral.sh/uv/0.5.1/install.sh | sh
  uv venv
  uv sync
  echo 'from .dev import *' >pasportaservo/settings/__init__.py
  uv run ./manage.py migrate
  uv run ./manage.py createsuperuser # Nur la uzantnomo kaj pasvorto estas deviga
  pre-commit install --install-hooks --overwrite
}

# Sistema pakaĝilo
function system_package_manager {
  debian_ubuntu || dnf_fedora
}

function debian_ubuntu {
  which apt || return 1
  sudo apt update
  sudo apt install git postgresql-server-dev-all postgresql-contrib postgis postgresql-postgis build-essential gcc libjpeg-dev zlib1g-dev libgdal-dev
}

function dnf_fedora {
  #TODO:FAROTE: Testi je fedora aŭ eĉ en virtuala maŝino de fedora
  which dnf || return 1
  sudo dnf install git redhat-rpm-config zlib-devel libjpeg-devel libzip-devel postgresql-server postgresql-contrib postgresql-devel gcc-c++ gdal
}

main "$@"
