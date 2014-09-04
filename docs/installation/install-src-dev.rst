.. index:: install-src-dev

.. _install_from_source-chapter:

Installing from source
======================

Setting up environment
----------------------

You may need to run this as the *root* user depending on how node.js was 
installed
::
  which lessc
  # if you do not have this installed then run:
  npm install -g less


Socorro can install the dependencies into a virtualenv for you.
You only need to run this once
::
  export PATH=$PATH:/usr/pgsql-9.3/bin/
  make bootstrap

Before running any Socorro components, always make sure that the virtualenv 
is activated and the PYTHONPATH is set
::
  . socorro-virtualenv/bin/activate
  export PYTHONPATH=.

Or you can choose to manage the virtualenv yourself, perhaps using
virtualenwrapper.

Run unit/functional tests
-------------------------

From inside the Socorro checkout
::
  make test database_username=test database_password=aPassword


Install stackwalker
-------------------

This is the binary which processes breakpad crash dumps into stack traces.
You must build it with GCC 4.6 or above.

If you are using RHEL/CentOS and installed GCC from the devtoolset repo
(per the installation instructions), make sure to "activate" it:
::
  scl enable devtoolset-1.1 bash

Then compile breakpad and the stackwalker binary:
::
  make breakpad stackwalker

Populate PostgreSQL Database
----------------------------

Load Socorro schema plus test products:
::
  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad \
    --fakedata --dropdb

Create partitioned tables
-------------------------

Normally this is handled automatically by the cronjob scheduler
:ref:`crontabber-chapter` but can be run as a one-off:
::
  python socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force

Sync Django database
--------------------

Django needs to write its ORM tables:
::
  cd webapp-django
  ./manage.py syncdb --noinput

Run socorro in dev mode
-----------------------

Copy default config files
::
  cp config/alembic.ini-dist config/alembic.ini
  cp config/collector.ini-dist config/collector.ini
  cp config/processor.ini-dist config/processor.ini
  cp config/middleware.ini-dist config/middleware.ini
  cp webapp-django/crashstats/settings/local.py-dist \
    webapp-django/crashstats/settings/local.py

You may need to edit these config files - for example collector (which is
generally a public service) might need listen on the correct IP address.

In particular, for login to work you want to modify the following
in webapp-django/crashstats/settings/local.py:
::
  SESSION_COOKIE_SECURE = False
  # Make sure to comment out the CACHES section so the default (memcached)
  # is used - NOTE login will not work until this is done
  #CACHES = {
  #    'default': {
  #        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
  #        'LOCATION': 'crashstats'
  #    }
  #}

Run Socorro services using Honcho (configured in Procfile)
::
  honcho start

The port numbers will be printed near the start of the output.
The web UI will be on port 5000, collector on 5100, middleware on 5200.

Alternatively you can also start individual services:
::
  honcho start web
  honcho start collector
  honcho start middleware
  honcho start processor

Note the port number when they start up, it will be different than if
you start all services together (starts at port 5000)

If you want to modify something that is common across config files like
PostgreSQL username/hostname/etc, refer to config/common_database.ini-dist and
the "+include" line in the service-specific config files (such as
collector.ini and processor.ini). This is optional but recommended.

