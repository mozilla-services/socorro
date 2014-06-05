.. index:: installation-rhel

.. _rhel-chapter:

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
  # /etc/yum.repos.d/elasticsearch.repo
  [elasticsearch-0.90]
  name=Elasticsearch repository for 0.90.x packages
  baseurl=http://packages.elasticsearch.org/elasticsearch/0.90/centos
  gpgcheck=1
  gpgkey=http://packages.elasticsearch.org/GPG-KEY-elasticsearch
  enabled=1

Install `Devtools 1.1 repository <http://people.centos.org/tru/devtools-1.1/readme>`_, needed for stackwalker
::
  sudo wget http://people.centos.org/tru/devtools-1.1/devtools-1.1.repo -O /etc/yum.repos.d/devtools-1.1.repo

Now you can actually install the packages:
::
  sudo yum install postgresql93-server postgresql93-plperl \
    postgresql93-contrib postgresql93-devel subversion make rsync \
    subversion gcc-c++ python-devel python-pip mercurial git \
    libxml2-devel libxslt-devel java-1.7.0-openjdk python-virtualenv \
    npm devtoolset-1.1-gcc-c++ rabbitmq-server elasticsearch

Initialize and enable RabbitMQ on startup:
::
  sudo service rabbitmq-server start
  sudo chkconfig rabbitmq-server on

Initialize and enable PostgreSQL on startup:
::
  sudo service postgresql-9.3 initdb
  sudo service postgresql-9.3 start
  sudo chkconfig postgresql-9.3 on

Verify that the postgresql service is set to use the UTC time zone:
::
  sudo grep ^timezone /var/lib/pgsql/9.3/data/postgresql.conf

You'll need to restart postgresql if the configuration was updated:
::
  sudo service postgresql-9.3 restart
