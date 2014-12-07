.. index:: dev-services

.. _dev_services-chapter:

Installing services
===================
.. sidebar:: Breakpad client and symbols

   Socorro aggregates and reports on Breakpad crashes.
   Read more about `getting started with Breakpad <http://code.google.com/p/google-breakpad/wiki/GettingStartedWithBreakpad>`_.

   You will need to `produce symbols for your application <http://code.google.com/p/google-breakpad/wiki/LinuxStarterGuide#Producing_symbols_for_your_application>`_ and make these files available to Socorro.

Set up a VM with Vagrant
------------------------

Vagrant can be used to build a VM that supplies the basic dependency stack
required by Socorro. This is an alternative to setting up these services
manually in your local environment.

You'll need both VirtualBox (http://www.virtualbox.org/) and
Vagrant (http://vagrantup.com/) set up and ready to go.

Make sure that you don't already have a ``./socorro-virtualenv`` directory
created with a different architecture (e.g. running ``make bootstrap`` on a Mac),
otherwise you'll get odd errors about pip not existing, binaries being the wrong
architecture, and so on.

1. Clone the Socorro repository:
::
  git clone git://github.com/mozilla/socorro.git
  cd socorro

2. Provision the VM:
::
 vagrant up

This step will:

* Download the base image if it isn't already present.
* Boot the VM.
* Using Puppet, install and initialise the basic dependencies that Socorro
  needs.

3. Add entries to ``/etc/hosts`` on the **HOST** machine:
::
  10.11.12.13 crash-stats crash-reports socorro-api

You can get a shell in the VM as the user "vagrant" by running this
in your Socorro source checkout:
::
  vagrant ssh

Your git checkout on the host will automatically be shared with the VM in
``/home/vagrant/socorro`` .

.. _Vagrant: https://docs.vagrantup.com/v2/networking/forwarded_ports.html

RHEL/CentOS 6
-------------

Install the `EPEL repository <http://fedoraproject.org/wiki/EPEL>`_ (note that
while the EPEL package is from an `i386` tree it will work on `x86_64`):
::
  sudo rpm -ivh http://dl.fedoraproject.org/pub/epel/6/i386/epel-release-6-8.noarch.rpm

Install the `PostgreSQL repository <http://yum.pgrpms.org/repopackages.php>`_. 
This package will vary depending on your distribution and environment.
For example if you are running RHEL 6 on i386, you would do this:
::
  sudo rpm -ivh http://yum.postgresql.org/9.3/redhat/rhel-6-i386/pgdg-centos93-9.3-1.noarch.rpm

Install the `Elasticsearch repository <http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/setup-repositories.html>`_.
First the key:
::
  sudo rpm --import http://packages.elasticsearch.org/GPG-KEY-elasticsearch

Then the repository definition:
::
  sudo tee /etc/yum.repos.d/elasticsearch.repo >/dev/null <<EOF
  [elasticsearch-0.90]
  name=Elasticsearch repository for 0.90.x packages
  baseurl=http://packages.elasticsearch.org/elasticsearch/0.90/centos
  gpgcheck=1
  gpgkey=http://packages.elasticsearch.org/GPG-KEY-elasticsearch
  enabled=1
  EOF

Now you can actually install the packages:
::
  sudo yum install postgresql93-server postgresql93-plperl \
    postgresql93-contrib postgresql93-devel subversion make rsync \
    subversion gcc-c++ python-devel python-pip mercurial nodejs-less \
    git libxml2-devel libxslt-devel java-1.7.0-openjdk python-virtualenv npm \
    rabbitmq-server elasticsearch httpd mod_wsgi memcached daemonize

Enable Apache on startup:
::
  sudo service httpd start
  sudo chkconfig httpd on

Enable Memcached on startup:
::
  sudo service memcached start
  sudo chkconfig memcached on

Enable RabbitMQ on startup:
::
  sudo service rabbitmq-server start
  sudo chkconfig rabbitmq-server on

Initialize and enable PostgreSQL on startup:
::
  sudo service postgresql-9.3 initdb
  sudo service postgresql-9.3 start
  sudo chkconfig postgresql-9.3 on

Modify postgresql config
::
  sudo vi /var/lib/pgsql/9.3/data/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Allow local connections for PostgreSQL
::
  sudo vi /var/lib/pgsql/9.3/data/pg_hba.conf

Ensure that local connections are allowed:
::

  # IPv4 local connections:
  host    all             all             127.0.0.1/32            md5
  # IPv6 local connections:
  host    all             all             ::1/128                 md5

See http://www.postgresql.org/docs/9.3/static/auth-pg-hba-conf.html
for more information on this file.

You'll need to restart postgresql if the configuration was updated:
::
  sudo service postgresql-9.3 restart

Ubuntu 14.04 (Trusty)
----------------------

Add public keys for PostgreSQL and ElasticSearch Apt Repositories:
::
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
    sudo apt-key add -
  wget --quiet -O - http://packages.elasticsearch.org/GPG-KEY-elasticsearch | \
    sudo apt-key add -

Install dependencies
::
  sudo apt-get install python-software-properties
  # python 2.6
  sudo add-apt-repository ppa:fkrull/deadsnakes
  # postgresql 9.3
  sudo apt-add-repository 'deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main'
  # elasticsearch 0.9
  sudo apt-add-repository 'deb http://packages.elasticsearch.org/elasticsearch/0.90/debian stable main'
  sudo apt-get update
  sudo apt-get install build-essential subversion libpq-dev openjdk-7-jre \
    python-virtualenv python-dev postgresql-9.3 postgresql-plperl-9.3 \
    postgresql-contrib-9.3 postgresql-server-dev-9.3 rsync python2.6 \
    python2.6-dev libxslt1-dev git-core mercurial node-less rabbitmq-server \
    elasticsearch memcached apache2 libsasl2-dev

Modify postgresql config
::
  sudo vi /etc/postgresql/9.3/main/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Allow local connections for PostgreSQL
::
  sudo vi /etc/postgresql/9.3/main/pg_hba.conf

Ensure that local connections are allowed:
::
  # IPv4 local connections:
  host    all             all             127.0.0.1/32            md5
  # IPv6 local connections:
  host    all             all             ::1/128                 md5

See http://www.postgresql.org/docs/9.3/static/auth-pg-hba-conf.html
for more information on this file.

Restart PostgreSQL to activate config changes, if the above was changed
::
  sudo /usr/sbin/service postgresql restart

Mac OS X
--------

Install dependencies
::
  brew update
  brew install git gpp postgresql subversion rabbitmq memcached npm
  sudo easy_install virtualenv virtualenvwrapper pip
  sudo pip-2.7 install docutils
  brew install mercurial

Install lessc
::
  sudo npm install -g less

Set your PATH
::
  export PATH=/usr/local/bin:/usr/local/sbin:$PATH

Initialize and run PostgreSQL
::
  initdb -D /usr/local/pgsql/data -E utf8
  export PGDATA=/usr/local/pgsql/data
  pg_ctl start

Create a symbolic link to pgsql_socket
::
  mkdir /var/pgsql_socket/
  ln -s /private/tmp/.s.PGSQL.5432 /var/pgsql_socket/

Modify postgresql config
::
  sudo editor /usr/local/pgsql/data/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Restart PostgreSQL to activate config changes, if the above was changed
::
  pg_ctl restart

Start RabbitMQ
::
  rabbitmq-server
