# Uzo sur via loka komputilo:
#
# pip install fabric3
# fab deploy  # apriore 'staging'
# fab prod deploy
#
# Funkcias se vi havas la jenan sekcion en via .ssh/config:
#     Host ps
#     HostName pasportaservo.org

from fabric.api import env, local, prefix, require, run, settings, sudo, task

env.hosts = ["ps"]
env.user = "ps"
env.use_ssh_config = True
env.site = "staging"  # default
env.branch = "master"  # default


@task
def prod():
    env.site = "prod"
    env.branch = "prod"


@task
def staging():
    env.site = "staging"
    env.branch = "master"


@task
def push(remote="origin", branch="master", runlocal=True):
    command = f"git push {remote} {branch}"
    if runlocal:
        local(command)
    else:
        run(command)


@task
def pull(remote="origin", branch="master", runlocal=True):
    if runlocal:
        local(f"git pull --rebase {remote} {branch}")
    else:
        run("git checkout -- locale/*/django.mo")
        run(f"git pull {remote} {branch}")


@task
def checkout(remote="origin", branch="master", runlocal=True):
    command = f"git checkout {remote}/{branch}"
    if runlocal:
        local(command)
    else:
        run(command)


@task
def requirements():
    with settings(ok_ret_codes=[0, 1]):
        run(
            "pip install -Ur requirements.txt"
            " | grep -v -e 'Requirement already satisfied' -e 'Requirement already up-to-date'"
        )


@task
def updatestrings(runlocal=True, _inside_env=False):
    command = "./manage.py compilemessages"
    if not runlocal or runlocal == "False":
        if _inside_env:
            run(command)
        else:
            with prefix(f"workon {env.site}"):
                run(command)
            site_ctl(command="restart")
    else:
        local(command)


@task
def updatestatic():
    run("./manage.py compilejsi18n -l eo")
    run("./manage.py compilescss")
    extra_args = "--ignore=*.scss" if env.site == "prod" else ""
    run(f"./manage.py collectstatic --verbosity 0 --noinput {extra_args}")
    run("./manage.py compress --verbosity 0 --force")


@task
def migrate():
    run("./manage.py migrate --noinput")


@task
def site_ctl(command):
    require("site", provided_by=[staging, prod])

    sudo(f"systemctl {command} pasportaservo.{env.site}.service")


@task
def deploy(mode="full", remote="origin"):
    require("site", provided_by=[staging, prod])
    require("branch", provided_by=[staging, prod])

    with prefix(f"workon {env.site}"):
        checkout(remote, env.branch, False)
        pull(remote, env.branch, False)
        if mode == "full":
            requirements()
            updatestrings(False, _inside_env=True)
            updatestatic()
            migrate()
    if mode != "html":
        site_ctl(command="restart")
