.. index:: build-from-source

.. _build_from_source-chapter:

Building from source
======================

Clone the Socorro repository
----------------------------

If you haven't already, you'll need to clone the Socorro git repository:
::
  git clone git://github.com/mozilla/socorro.git
  cd socorro

Setting up environment
----------------------

Socorro can install python dependencies into a virtualenv for you.
You only need to run this once:
::
  export PATH=$PATH:/usr/pgsql-9.3/bin/
  make bootstrap

Before running any Socorro components, always make sure that the virtualenv 
is activated:
::
  . socorro-virtualenv/bin/activate

The Socorro package should be installed into the virtualenv too,
in "develop" mode so you only need to run this once:
::
  python setup.py develop

Add a new superuser account to PostgreSQL
-----------------------------------------

Create a superuser account for yourself. Make sure to put your username
and desired password instead of YOURNAME and YOURPASS.
As the *postgres* user:
::
  psql template1 -c \
    "create user YOURNAME with encrypted password 'YOURPASS' superuser"

For running unit tests, you'll want a test user as well (make sure
to remove this for production installs).
::
  psql template1 -c \
    "create user test with encrypted password 'aPassword' superuser"


Configure migrations (Alembic)
------------------------------

Also, before you run unit tests or make, be sure to copy and edit this file:
::
  cp config/alembic.ini-dist config/alembic.ini
  vi config/alembic.ini

The important line to update is *sqlalchemy.url*, it should be changed
to match the superuser account you created above:
::
  sqlalchemy.url = postgresql://YOURNAME:YOURPASS@localhost/socorro_migration_test


Run unit/functional tests
-------------------------

From inside the Socorro checkout
::
  make test database_username=test database_password=aPassword


Populate PostgreSQL Database
----------------------------

Load Socorro schema plus test products:
::
  socorro setupdb --database_name=breakpad --fakedata --dropdb

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

Run Socorro in dev mode
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

Troubleshooting
---------------

If you are seeing errors after starting Socorro with honcho, it may be
that a previous unsuccessful run didn't clean up all the Python processes.

You can inspect for such stray processes using ps:
::
  ps ax | grep python
