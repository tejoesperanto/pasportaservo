# Uzo sur via loka komputilo:
#
# pip install fabric3
# fab deploy  # apriore 'staging'
# fab prod deploy
#
# Funkcias se vi havas la jenan sekcion en via .ssh/config:
#     Host ps
#     HostName 188.166.58.162

from fabric.api import env, local, prefix, require, run, sudo, task

env.hosts = ['ps']
env.user = 'ps'
env.use_ssh_config = True
env.directory = '/srv/%s/pasportaservo'
env.site = 'staging'   # default
env.branch = 'master'  # default


@task
def prod():
    env.site = 'prod'
    env.branch = 'prod'


@task
def staging():
    env.site = 'staging'
    env.branch = 'master'


@task
def push(remote='origin', branch='master', runlocal=True):
    command = "git push %s %s" % (remote, branch)
    if runlocal:
        local(command)
    else:
        run(command)


@task
def pull(remote='origin', branch='master', runlocal=True):
    if runlocal:
        local("git pull --rebase %s %s" % (remote, branch))
    else:
        run("git checkout -- locale/*/django.mo")
        run("git pull %s %s" % (remote, branch))


@task
def checkout(remote='origin', branch='master', runlocal=True):
    command = "git checkout %s/%s" % (remote, branch)
    if runlocal:
        local(command)
    else:
        run(command)


@task
def requirements():
    run("pip install -Ur requirements.txt")


@task
def updatestrings(runlocal=True, _inside_env=False):
    command = "./manage.py compilemessages"
    if not runlocal or runlocal == 'False':
        if _inside_env:
            run(command)
        else:
            with prefix("workon %s" % env.site):
                run(command)
            sudo("supervisorctl restart %s" % env.site)
    else:
        local(command)


@task
def updatestatic():
    run("./manage.py compilescss")
    run("./manage.py collectstatic --noinput %s" %
        ("--ignore=*.scss" if env.site == 'prod' else ""))
    run("./manage.py compress --force")


@task
def migrate():
    run("./manage.py migrate --noinput")


@task
def deploy(mode='full', remote='origin'):
    require('site', provided_by=[staging, prod])
    require('branch', provided_by=[staging, prod])

    with prefix("workon %s" % env.site):
        checkout(remote, env.branch, False)
        pull(remote, env.branch, False)
        if mode == 'full':
            requirements()
            updatestrings(False, _inside_env=True)
            updatestatic()
            migrate()
    if mode != 'html':
        sudo("supervisorctl restart %s" % env.site)
