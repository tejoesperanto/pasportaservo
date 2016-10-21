# Uzo sur via loka komputilo:
#
# pip install fabric3
# fab deploy  # apriore staging
# fab prod deploy
#
# Funkcias se vi havas "Host ps" sekcio en via .ssh/config
# kaj 'tejo' remote al git@github.com:tejo-esperanto/pasportaservo.git

from fabric.api import local, run, sudo, env, prefix, require


env.hosts = ['ps']
env.user = 'ps'
env.use_ssh_config = True
env.directory = '/srv/%s/pasportaservo'
env.site = 'staging'  # default


def prod():
    env.site = 'prod'


def staging():
    env.site = 'staging'


def push(branch='master', remote='tejo', runlocal=True):
    command = 'git push %s %s' % (remote, branch)
    if runlocal:
        local(command)
    else:
        run(command)


def pull(branch='master', remote='tejo', runlocal=True):
    if runlocal:
        local('git pull --rebase %s %s' % (remote, branch))
    else:
        run('git pull %s %s' % (remote, branch))


def sync(branch='master', remote='origin', runlocal=True):
    pull(branch, remote, runlocal)
    push(branch, remote, runlocal)


def requirements():
    run('pip install -Ur requirements.txt')


def collectstatic():
    run("./manage.py collectstatic --noinput")


def migrate():
    run("./manage.py migrate --noinput")


def deploy(branch='devel', remote='origin'):
    require('site', provided_by=[staging, prod])
    branch = 'master' if env.site == 'prod' else branch

    with prefix('workon %s' % env.site):
        pull(branch, remote, False)
        requirements()
        collectstatic()
        migrate()
    sudo("supervisorctl restart %s" % env.site)
