# DEPLOYMENT


## Install on a new production server
ps@ps:~$ `sudo apt install nginx libpq-dev python3-dev python3-pip supervisor mercurial git vim postgresql autopostgresqlbackup`

ps@ps:~$ `ssh-keygen`
Generating public/private rsa key pair.
Enter file in which to save the key (/home/ps/.ssh/id_rsa): *Enter*
Enter passphrase (empty for no passphrase): *Enter*
Enter same passphrase again: *Enter*
Your identification has been saved in /home/ps/.ssh/id_rsa.
Your public key has been saved in /home/ps/.ssh/id_rsa.pub.
The key fingerprint is:
4b:85:03:e8:d1:d6:9c:d7:9b:09:46:3d:8a:ce:69:82 ps@ps
The key's randomart image is:
+---[RSA 2048]----+
|     o.o o.o     |
|    o o.+.+ +    |
|   . o  o+.o =   |
|    .   .o. +    |
|     . oS.       |
|    E ..=.       |
|       o.        |
|                 |
|                 |
+-----------------+
ps@ps:~$ `cat ~/.ssh/id_rsa.pub`
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDDjRRf//bqeEh1AiOVwsE88vpMnl/3Lmeon6YjcZ+KKFypjorEeVujYM9ji71Y5ihJvd6taYslF0+cJX1kpxunSpdaJRqmu07YI+RiFvooNMiVJlsC5n2oK/WYtGd1UeY8yxrjZ1b9nG9zkgfp50yCUgq2h6gfx5O+9289yLHtN3UTx/uZDAOqsVtVfJZv4Bnd9UozFuX3nd2mPRur2I2coqabxa24r/R/EUVinpULwz0BVy3VtHdNUMrvDnOXFhJxGby3hIVI2NbQwNMsu0Jbr9IvCx7T6vaxbCxGiif5nraabCfQcVQz5HdN+67novXTZAlBzMbyjhTMjVxKtBz/ ps@ps

Copy this key in the [Deploy Keys in Bitbucket]( https://bitbucket.org/pasportaservo/pasportaservo/admin/deploy-keys/)

ps@ps:~$ `sudo mkdir /srv/pasportaservo`
ps@ps:~$ `cd /srv/`
ps@ps:/srv$ `chown ps pasportaservo/`
ps@ps:/srv$ `hg clone ssh://hg@bitbucket.org/pasportaservo/pasportaservo`
The authenticity of host 'bitbucket.org (131.103.20.168)' can't be established.
RSA key fingerprint is 97:8c:1b:f2:6f:14:6b:5c:3b:ec:aa:46:46:74:7c:40.
Are you sure you want to continue connecting (yes/no)? *yes*
remote: Warning: Permanently added 'bitbucket.org,131.103.20.168' (RSA) to the list of known hosts.
destination directory: pasportaservo
requesting all changes
adding changesets
adding manifests
adding file changes
added 187 changesets with 718 changes to 210 files
updating to branch default
187 files updated, 0 files merged, 0 files removed, 0 files unresolved

#### Creating the environment
ps@ps:~$ `sudo pip3 install virtualenvwrapper`
ps@ps:~$ `sudo mkdir /opt/envs`
ps@ps:~$ `sudo chgrp ps /opt/envs`
ps@ps:~$ `sudo chmod 775 /opt/envs`

Add these lines at the bottom of ~/.bashrc

ps@ps:~$ `vim ~/.bashrc`

    # virtualenvwrapper
    export WORKON_HOME=/opt/envs
    export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
    source /usr/local/bin/virtualenvwrapper.sh

ps@ps:~$ `source ~/.bashrc`
ps@ps:~$ `mkvirtualenv ps`
(ps)ps@ps:~$ `cd /srv/pasportaservo`
(ps)ps@ps:/srv/pasportaservo$ `pip install -r requirements/base.txt`

#### Configuring PostgreSQL
ps@ps:~$ `sudo -u postgres createuser ps --interactive`   --interactive
    Shall the new role be a superuser? (y/n) *n*
    Shall the new role be allowed to create databases? (y/n) *y*
    Shall the new role be allowed to create more new roles? (y/n) *n*

ps@ps:~$ `zcat pasportaservo_2015-11-23_07h35m.lundo.sql.gz | psql -d ps`

#### Starting Django
(ps)ps@ps:/srv/pasportaservo/pasportaservo/settings$ `ln -s prod.py local_settings.py`
(ps)ps@ps:/srv/pasportaservo$ `mkdir static`

Copy the `media` folder in `static`

(ps)ps@ps:/srv/pasportaservo$ `dj collectstatic`
(ps)ps@ps:/srv/pasportaservo$ `dj runserver` to test and then Ctrl-C
