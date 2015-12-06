# INSTALI

This project is using and Django 1.7. See requirements.txt.

You will need Python 2.7 or 3.4, PostgreSQL, PIP and Virtualenv:

    sudo apt-get install postgresql postgresql-client postgresql-client-common libpq5 libpq-dev python3 python3-dev
    sudo apt-get install mercurial
    sudo apt-get install python-setuptools
    easy_install --user pip
    sudo pip install virtualenv

If it's possible, don't install Django on your system, but just in a virtualenv. This way you will get an error if you're not in a proper virtualenv.

    sudo -u postgres createuser my-username --interactive

And answer 'n' to all questions.

    sudo -u postgres createdb -O my-username -l eo.utf8 -E utf8 pasportaservo

Go to https://bitbucket.org/pasportaservo/pasportaservo/ and fork it to your own account. You should have the repository on https://bitbucket.org/my-username/pasportaservo/

    hg clone ssh://hg@bitbucket.org/my-username/pasportaservo

or

    hg clone https://my-username@bitbucket.org/my-username/pasportaservo

    cd pasportaservo
    virtualenv env --system-site-packages
    source env/bin/activate
    pip install -r requirements.txt  # or requirements/dev.txt
    python manage.py migrate

    cd pasportaservo/settings
    ln -s my-local-settings.py local_settings.py
    cd -

> `my-local-settings.py` can be `dev.py`, `staging.py` or `prod.py`  

    python manage.py runserver

Then type in your web browser: `localhost:8000`  



## Understanding the codebase

- **pasportaservo/**: general folder, with configuration, base-level URLs…
- **hosting/**: main application for hosting


**Important files in hosting:**

- models.py: data structure
- urls.py: links between URLs and views
- views.py: what kind of page to display
- templates/: pseudo HTML files
