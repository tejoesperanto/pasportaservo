# Uzo sur via loka komputilo:
#
# python3 -m pip install fabric
# fab -H ps --prompt-for-login-password staging deploy
# fab -H ps --prompt-for-login-password prod deploy
#
# Funkcias se vi havas la jenan sekcion en via .ssh/config:
#     Host ps
#     HostName pasportaservo.org

import sys

from fabric import task

env = {}


@task
def prod(conn):
    if env:
        sys.exit(f"Site [{env['site']}] and branch [{env['branch']}] are already configured!")
    env['site'] = "prod"
    env['branch'] = "prod"


@task
def staging(conn):
    if env:
        sys.exit(f"Site [{env['site']}] and branch [{env['branch']}] are already configured!")
    env['site'] = "staging"
    env['branch'] = "master"


def _init_venv_string():
    return f"source ~/.bash_profile; workon {env['site']}"


@task(auto_shortflags=False)
def pull(conn, remote="origin", branch="master", runlocal=True):
    if runlocal:
        conn.local(f"git pull --rebase {remote} {branch}")
    else:
        conn.run("git checkout -- locale/*/django*.mo")
        conn.run("git status")
        conn.run(f"git pull {remote} {branch}", pty=True)


@task(auto_shortflags=False)
def checkout(conn, remote="origin", branch="master", runlocal=True):
    command = f"git checkout {remote}/{branch}"
    if runlocal:
        conn.local(command)
    else:
        conn.run(command)


@task(auto_shortflags=False)
def requirements(conn, runlocal=False, inside_env=False):
    command = (
        f"python3 -m pip install -Ur requirements{'/dev' if runlocal else ''}.txt"
        " | grep -v -e 'Requirement already satisfied' -e 'Requirement already up-to-date'"
    )
    if runlocal:
        result = conn.local(command, warn=True)
    else:
        if not inside_env:
            if not env:
                sys.exit("Site not defined, use staging/prod.")
            with conn.prefix(_init_venv_string()):
                result = conn.run(command, warn=True, pty=True)
        else:
            result = conn.run(command, warn=True, pty=True)

    if result.exited not in (0, 1):
        sys.exit(result.exited)
    if not runlocal and not inside_env:
        site_ctl(conn, command="restart")
        site_ctl(conn, command="status", needs_su=False)


@task(auto_shortflags=False)
def makestrings(conn, locale="eo", runlocal=True):
    if runlocal:
        command = (
            "python3 ./manage.py makemessages"
            f" --locale {locale} --ignore \"htmlcov/*\" --add-location=file"
        )
        conn.local(command)
    # Remote generation is not supported.


@task(auto_shortflags=False)
def updatestrings(conn, runlocal=True, inside_env=False):
    command = "python3 ./manage.py compilemessages"
    if not runlocal:
        if not inside_env:
            if not env:
                sys.exit("Site not defined, use staging/prod.")
            with conn.prefix(_init_venv_string()):
                conn.run(command)
            site_ctl(conn, command="restart")
            site_ctl(conn, command="status", needs_su=False)
        else:
            conn.run(command)
    else:
        conn.local(command)


@task
def updatestatic(conn):
    conn.run("./manage.py compilejsi18n -l eo")
    conn.run("./manage.py compilescss")
    extra_args = "--ignore=*.scss" if env['site'] == "prod" else ""
    conn.run(
        f"./manage.py collectstatic --verbosity 1 --noinput {extra_args}"
        " | grep -v 'Found another file with the destination path' "
    )
    conn.run("./manage.py compress --verbosity 0 --force")


@task
def migrate(conn):
    conn.run("./manage.py migrate --noinput")


@task(auto_shortflags=False)
def site_ctl(conn, command, service_name="pasportaservo", needs_su=True):
    if not env:
        sys.exit("Site not defined, use staging/prod.")

    conn.run(
        ("sudo " if needs_su else "")
        + f"systemctl {command} {service_name}.{env['site']}.service",
        pty=True)


@task(auto_shortflags=False)
def deploy(conn, mode="full", remote="origin"):
    if not env:
        sys.exit("Site not defined, use staging/prod.")

    with conn.prefix(_init_venv_string()):
        checkout(conn, remote, env['branch'], runlocal=False)
        pull(conn, remote, env['branch'], runlocal=False)
        if mode == "full":
            requirements(conn, runlocal=False, inside_env=True)
            updatestrings(conn, runlocal=False, inside_env=True)
            updatestatic(conn)
            migrate(conn)
    if mode != "html":
        site_ctl(conn, command="restart")
        site_ctl(conn, command="status", service_name="memcached-ps", needs_su=False)
        site_ctl(conn, command="status", needs_su=False)
