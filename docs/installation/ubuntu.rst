.. index:: installation-ubuntu

.. _ubuntu-chapter:

Ubuntu 12.04 (Precise)
----------------------

Add the `PostgreSQL Apt repository <http://www.postgresql.org/download/linux/ubuntu/>`_:
::
  # /etc/apt/sources.list.d/pgdg.list
  deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main

Add the public key for the PostgreSQL Apt Repository:
::
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
    sudo apt-key add -

Add the `Elasticsearch repository <http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/setup-repositories.html>`_:
::
  # /etc/apt/sources.list.d/elasticsearch.list
  deb http://packages.elasticsearch.org/elasticsearch/0.90/debian stable main

Add the public key for the Elasticsearch repository:
::
  wget --quiet -O - http://packages.elasticsearch.org/GPG-KEY-elasticsearch | \
    sudo apt-key add -

Install dependencies
::
  sudo apt-get install python-software-properties
  # needed for python2.6
  sudo add-apt-repository ppa:fkrull/deadsnakes
  sudo apt-get update
  sudo apt-get install build-essential subversion libpq-dev openjdk-7-jre \
    python-virtualenv python-dev postgresql-9.3 postgresql-plperl-9.3 \
    postgresql-contrib-9.3 postgresql-server-dev-9.3 rsync python2.6 \
    python2.6-dev libxslt1-dev git-core mercurial node-less rabbitmq-server \
    elasticsearch memcached apache2

Modify postgresql config
::
  sudo editor /etc/postgresql/9.3/main/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Restart PostgreSQL to activate config changes, if the above was changed
::
  sudo /usr/sbin/service postgresql restart
