.. index:: installation-ubuntu

.. _ubuntu-chapter:

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
