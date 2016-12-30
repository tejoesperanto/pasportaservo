# Uzo sur via loka komputilo:
#
# pip install fabric3
# fab deploy  # apriore staging
# fab prod deploy
#
# Funkcias se vi havas "Host ps" sekcio en via .ssh/config

from fabric.api import task, local, run, sudo, env, prefix, require


env.hosts = ['ps']
env.user = 'ps'
env.use_ssh_config = True
env.directory = '/srv/%s/pasportaservo'
env.site = 'staging'  # default
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
    command = 'git push %s %s' % (remote, branch)
    if runlocal:
        local(command)
    else:
        run(command)

@task
def pull(remote='origin', branch='master', runlocal=True):
    if runlocal:
        local('git pull --rebase %s %s' % (remote, branch))
    else:
        run('git pull %s %s' % (remote, branch))

@task
def checkout(remote='origin', branch='master', runlocal=True):
    command = 'git checkout %s/%s' % (remote, branch)
    if runlocal:
        local(command)
    else:
        run(command)

@task
def requirements():
    run('pip install -Ur requirements.txt')

@task
def collectstatic():
    run("./manage.py collectstatic --noinput")

@task
def migrate():
    run("./manage.py migrate --noinput")

@task
def deploy(branch='devel', remote='origin'):
    require('site', provided_by=[staging, prod])
    require('branch', provided_by=[staging, prod])

    with prefix('workon %s' % env.site):
        checkout(remote, env.branch, False)
        pull(remote, env.branch, False)
        requirements()
        collectstatic()
        migrate()
    sudo("supervisorctl restart %s" % env.site)
