.. index:: production-install

.. _production_install-chapter:

Production Install
==================

Currently Socorro is supported on CentOS 7

For any other platform, you must build from source. See
:ref:`development-chapter` for more information.


.. sidebar:: Breakpad client and symbols

   Socorro aggregates and reports on Breakpad crashes.
   Read more about `getting started with Breakpad <http://code.google.com/p/google-breakpad/wiki/GettingStartedWithBreakpad>`_.

   You will need to `produce symbols for your application <http://code.google.com/p/google-breakpad/wiki/LinuxStarterGuide#Producing_symbols_for_your_application>`_ and make these files available to Socorro.

Installing services
-------------------

Install the EPEL repository.
::
  sudo yum install epel-release

Install the PostgreSQL repository.
::
  sudo rpm -ivh http://yum.postgresql.org/9.3/redhat/rhel-7-x86_64/pgdg-centos93-9.3-1.noarch.rpm

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

Ensure yum cache is up to date.
::
  sudo yum makecache

Install the Socorro repository.
::
  sudo rpm -ivh https://s3-us-west-2.amazonaws.com/org.mozilla.crash-stats.packages-public/el/7/noarch/socorro-public-repo-1-1.el7.centos.noarch.rpm

Now you can actually install the packages:
::
  sudo yum install postgresql93-server postgresql93-plperl \
    postgresql93-contrib java-1.7.0-openjdk python-virtualenv \
    rabbitmq-server elasticsearch nginx envconsul consul memcached socorro

Enable Memcached on startup:
::
  sudo systemctl enable nginx

Enable Memcached on startup:
::
  sudo systemctl enable memcached

Enable RabbitMQ on startup:
::
  sudo systemctl enable rabbitmq-server

Enable Elasticsearch on startup:
::
  sudo systemctl enable elasticsearch

Initialize and enable PostgreSQL on startup:
::
  sudo service postgresql-9.3 initdb
  sudo systemctl enable postgresql-9.3

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
  host    all             all             127.0.0.1/32            trust
  # IPv6 local connections:
  host    all             all             ::1/128                 trust

See http://www.postgresql.org/docs/9.3/static/auth-pg-hba-conf.html
for more information on this file.

You'll need to restart postgresql if the configuration was updated:
::
  sudo systemctl restart postgresql-9.3

Disable SELinux
---------------

Socorro currently requires that SELinux is disabled:
::
  sudo vi /etc/sysconfig/selinux

Ensure that SELINUX is set to permissive:
::
  SELINUX=permissive

Reboot the system if the above was changed:
::
  sudo shutdown -r now
