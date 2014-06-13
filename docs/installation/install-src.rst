.. index:: install-src

.. _install_from_source-chapter:

Installing from source
======================

Setting up environment
----------------------

To run and hack on Socorro apps, you will need:

1) all dependencies installed from requirements.txt
2) to have your PYTHONPATH set to the location of the socorro checkout
3) The Django web service and its tests need the LESS preprocessor to be installed and on your $PATH

You may need to run this as the *root* user depending on how node.js was 
installed
::
  npm install -g less


Socorro can install the dependencies into a virtualenv for you.
You only need to run this once
::
  export PATH=$PATH:/usr/pgsql-9.3/bin/
  make bootstrap bootstrap-webapp

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
  make test test-webapp database_username=test database_password=aPassword


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

Load the Socorro schema
-------------------

If you want to hack on Socorro, or just see what a functional system looks
like, you also have the option to generate and populate the DB with synthetic
test data
::
  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad \
    --fakedata --dropdb

IMPORTANT NOTE - many reports use the reports_clean_done() stored
procedure to check that reports exist for the last UTC hour of the
day being processed, as a way to catch problems. If your crash
volume does not guarantee one crash per hour, you may want to modify
this function in
socorro/external/postgresql/raw_sql/procs/reports_clean_done.sql
and reload the schema


Create partitioned reports_* tables
------------------------------------------
Socorro uses PostgreSQL partitions for the reports table, which must be created
on a weekly basis.

Normally this is handled automatically by the cronjob scheduler
:ref:`crontabber-chapter` but can be run as a one-off:
::
  python socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force

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

By default they listen on localhost only, which should be fine for local
development.

Run Socorro services using Honcho (configured in Procfile)
::
  honcho start

Alternatively you can also start individual services:
::
  honcho start web
  honcho start collector
  honcho start middleware
  honcho start processor

If you want to modify something that is common across config files like
PostgreSQL username/hostname/etc, refer to config/common_database.ini-dist and
the "+include" line in the service-specific config files (such as
collector.ini and processor.ini). This is optional but recommended.

.. _prodinstall-chapter:

Production install (RHEL/CentOS)
================================

The only supported production configuration for Socorro right now is
RHEL (CentOS or other clones should work as well) but it should be
fairly straightforward to get going on any OS or Linux distribution,
assuming you know how to add users, install services and get WSGI running
in your web server (we recommend Apache with mod_wsgi at this time).

Install production dependencies
-------------------------------

Set up directories and permissions

As the *root* user:
::
  mkdir /etc/socorro
  mkdir /var/log/socorro
  mkdir -p /data/socorro
  useradd socorro
  chown socorro:socorro /var/log/socorro
  mkdir /home/socorro/primaryCrashStore /home/socorro/fallback /home/socorro/persistent
  chown apache /home/socorro/primaryCrashStore /home/socorro/fallback
  chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback

Ensure that the user doing installs owns the install dir,
as the *root* user:
::
  chown socorro /data/socorro

Install socorro
---------------

From inside the Socorro checkout (as the user that owns /data/socorro):
::
  make install

By default, this installs files to /data/socorro. You can change this by
specifying the PREFIX:
::
  make install PREFIX=/usr/local/socorro

However if you do change this default, then make sure this is reflected in all
files in /etc/socorro and also the WSGI files (described below).

Install configuration to system directory
-----------------------------------------

From inside the Socorro checkout, as the *root* user
::
  cp config/*.ini-dist /etc/socorro

Make sure the copy each .ini-dist file to .ini and configure it.

In particular, you must change the web server in collector.ini
and middlware.ini to support Apache mod_wsgi rather than the standalone
server::
  wsgi_server_class='socorro.webapi.servers.ApacheModWSGI'

It is highly recommended that you customize the files
to change default passwords, and include the common_*.ini files
rather than specifying the default password in each config file.

Install Socorro cron job manager
--------------------------------

Socorro's cron jobs are managed by :ref:`crontabber-chapter`.

:ref:`crontabber-chapter` runs every 5 minutes from the system crontab.

Socorro ships an RC file, intended for use by cron jobs. This contains
common configuration like the path to the Socorro install, and some
convenience functions.

From inside the Socorro checkout, as the *root* user
::
  cp scripts/crons/socorrorc /etc/socorro/
  cp config/crontab-dist /etc/cron.d/socorro

Start daemons
-------------


The processor daemon must be running. You can
find startup scripts for RHEL/CentOS in:

https://github.com/mozilla/socorro/tree/master/scripts/init.d

Copy this into /etc/init.d and enable on boot:

From inside the Socorro checkout, as the *root* user
::
  cp scripts/init.d/socorro-processor /etc/init.d/
  chkconfig --add socorro-processor
  chkconfig socorro-processor on
  service socorro-processor start

Web Services
------------

Socorro requires three web services. If you are using Apache, the recommended
configuration is to run these on separate subdomains as Apache Virtual Hosts:

* crash-stats   - the web UI for viewing crash reports (Django)
* socorro-api   - the "middleware" used by the web UI
* crash-reports - the "collector" receives reports from crashing clients
                  via HTTP POST

Ensure that crash-stats is pointing to the local socorro-api server, and
also that dev/debug/etc. options are disabled.
edit /data/socorro/webapp-django/crashstats/settings/local.py:
::
  CACHE_MIDDLEWARE = True
  CACHE_MIDDLEWARE_FILES = False
  MWARE_BASE_URL = 'http://localhost/bpapi'
  MWARE_HTTP_HOST = 'socorro-api'
  DATABASES = {
    # adjust the postgres example for your install
  }
  DEBUG = TEMPLATE_DEBUG = False
  DEV = False
  COMPRESS_OFFLINE = True
  SECRET_KEY = '' # set this to something unique
  # adjust this for your site!
  ALLOWED_HOSTS = ['crash-stats.example.com']
  # If you are running HTTPS set to True, otherwise False
  # NOTE this is needed for login to work
  SESSION_COOKIE_SECURE = True
  # Make sure to comment out the CACHES section so the default (memcached)
  # is used - NOTE login will not work until this is done
  #CACHES = {
  #    'default': {
  #        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
  #        'LOCATION': 'crashstats'
  #    }
  #}


Allow Django to create the database tables it needs for managing sessions:
::
  /data/socorro/socorro-virtualenv/bin/python \
    /data/socorro/webapp-django/manage.py syncdb --noinput

Copy the example Apache config into place from the Socorro checkout as the
*root* user:
::
  cp config/apache.conf-dist /etc/httpd/conf.d/socorro.conf

Make sure to customize /etc/httpd/conf.d/socorro.conf and restart Apache when
finished, as the *root* user:
::
  service httpd restart
