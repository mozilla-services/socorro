.. index:: installation

.. _installation-chapter:

Installation
============

How Socorro Works
````````````

Socorro is a set of components for collecting, processing and reporting on crashes. It is used by Mozilla for tracking crashes of Firefox, B2G, Thunderbird and other projects. The production Mozilla install is public and hosted at https://crash-stats.mozilla.com/

The components which make up Socorro are:

* Collector - collects breakpad minidump crashes which come in over HTTP POST
* Processor - turn breakpad minidump crashes into stack traces and other info
* Middleware - provide HTTP REST interface for JSON reports and real-time data
* Web UI aka crash-stats - django-based web app for visualizing crash data

There are two main functions of Socorro:

1) collect, process, and allow for real-time searches and results for individual crash reports

  This requires both RabbitMQ and PostgreSQL, as well as the Collector,
  Processor and Middleware and Web UI.

  Individual crash reports are pulled from long-term storage using the
  /report/index/ page, for example: https://crash-stats.mozilla.com/report/index/ba8c248f-79ff-46b4-97b8-a33362121113

  The search feature is at: https://crash-stats.mozilla.com/query
  There is a new version which uses Elastic Search and will eventually replace
  the above:
  https://crash-stats.mozilla.com/search/

2) a set of batch jobs which compiles aggregate reports and graphs, such as "Top Crashes by Signature"

  This requires PostgreSQL, Middleware and Web UI. It is triggered once per day
  by the "daily_matviews" cron job, covering data processed in the previous UTC
  day.

  Every other page on https://crash-stats.mozilla.com is of this type, for example the Topcrashers report: https://crash-stats.mozilla.com/topcrasher/byversion/Firefox

Installation Requirements
````````````

.. sidebar:: Breakpad client and symbols

   Socorro aggregates and reports on Breakpad crashes.
   Read more about `getting started with Breakpad <http://code.google.com/p/google-breakpad/wiki/GettingStartedWithBreakpad>`_.

   You will need to `produce symbols for your application <http://code.google.com/p/google-breakpad/wiki/LinuxStarterGuide#Producing_symbols_for_your_application>`_ and make these files available to Socorro.

* Mac OS X or Linux (Ubuntu/RHEL)
* PostgreSQL 9.3
* RabbitMQ 3.1
* Python 2.6
* C++ compiler (GCC 4.6 or greater)
* Subversion
* Git
* PostrgreSQL and Python dev libraries (for psycopg2)

Virtual Machine using Vagrant
````````````

Vagrant can be used to build and run a full Socorro VM (CentOS Linux) on a
Mac OS X, Windows or Linux host.

1. Clone Socorro repository
::
  git clone git://github.com/mozilla/socorro.git
  cd socorro/

2. Install VirtualBox from:
http://www.virtualbox.org/

3. Install Vagrant from:
http://vagrantup.com/

4. Download and copy base box, boot VM and provision it with puppet:
::
 vagrant up

5. Add to /etc/hosts (on the HOST machine!):
::
  10.11.12.13 crash-stats crash-reports socorro-api

If everything works, you'll now have a VM running with all of Socorro's
dependencies installed and ready for you!

Your git checkout will automatically be shared with the VM in
/home/vagrant/src/socorro, you can access it like so:
::
 vagrant ssh
 cd src/socorro

Make sure that you don't already have a ./socorro-virtualenv directory
created with a different architecture! Otherwise you'll get odd errors
about pip not existing, binaries being the wrong architecture and so on.

Now continue in the install docs, starting from: :ref:`settingupenv-chapter`

Mac OS X
````````````
Install dependencies
::
  brew update
  brew tap homebrew/versions
  brew install python26 git gpp postgresql subversion rabbitmq
  sudo easy_install virtualenv virtualenvwrapper pip
  sudo pip-2.7 install docutils
  brew install mercurial

Set your PATH
::
  export PATH=/usr/local/bin:$PATH

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

Now continue in the install docs, starting from: :ref:`gitclone-chapter`

Ubuntu 12.04 (Precise)
````````````

Add PostgreSQL Apt repository http://www.postgresql.org/download/linux/ubuntu/
Create the file /etc/apt/sources.list.d/pgdg.list:
::
  deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main

Add the public key for the PostgreSQL Apt Repository:
::
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
  sudo apt-key add -

Install dependencies
::
  sudo apt-get install python-software-properties
  # needed for python2.6
  sudo add-apt-repository ppa:fkrull/deadsnakes
  sudo apt-get update
  sudo apt-get install build-essential subversion libpq-dev python-virtualenv python-dev postgresql-9.3 postgresql-plperl-9.3 postgresql-contrib-9.3 postgresql-server-dev-9.3 rsync python2.6 python2.6-dev libxslt1-dev git-core mercurial rabbitmq-server

Modify postgresql config
::
  sudo editor /etc/postgresql/9.3/main/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Create a superuser for your account (substitute your username for $USER):
As the *postgres* user:
::
  createuser -s $USER
  psql -c "ALTER USER $USER WITH ENCRYPTED PASSWORD 'aPassword'"

Restart PostgreSQL to activate config changes, if the above was changed
::
  sudo /usr/sbin/service postgresql restart

Now continue in the install docs, starting from: :ref:`gitclone-chapter`

RHEL/CentOS 6
````````````

Install `EPEL repository <http://fedoraproject.org/wiki/EPEL>`_
::
  rpm -ivh http://dl.fedoraproject.org/pub/epel/6/i386/epel-release-6-8.noarch.rpm

Install `PGDG repository <http://yum.pgrpms.org/>`_
::
  rpm -ivh http://yum.pgrpms.org/9.3/redhat/rhel-6-i386/pgdg-centos93-9.3-1.noarch.rpm

Install `Elastic Search repository <http://www.elasticsearch.org/>`_
::
  rpm -ivh 'https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-0.90.4.noarch.rpm'

Install `Devtools 1.1 repository <http://people.centos.org/tru/devtools-1.1/readme>`_, needed for stackwalker
::
  wget http://people.centos.org/tru/devtools-1.1/devtools-1.1.repo -O /etc/yum.repos.d/devtools-1.1.repo

Install dependencies

As the *root* user:
::
  yum install postgresql93-server postgresql93-plperl postgresql93-contrib postgresql93-devel subversion make rsync subversion gcc-c++ python-devel python-pip mercurial git libxml2-devel libxslt-devel java-1.7.0-openjdk python-virtualenv npm devtoolset-1.1-gcc-c++ rabbitmq-server

Initialize and enable RabbitMQ on startup

As the *root* user:
::
  service rabbitmq-server initdb
  service rabbitmq-server start
  chkconfig rabbitmq-server on

Initialize and enable PostgreSQL on startup

As the *root* user:
::
  service postgresql-9.3 initdb
  service postgresql-9.3 start
  chkconfig postgresql-9.3 on

Modify postgresql config

As the *root* user:
::
  vi /var/lib/pgsql/9.3/data/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Allow local connections for PostgreSQL

Client authentication is controlled in the pg_hba.conf file, see
http://www.postgresql.org/docs/9.3/static/auth-pg-hba-conf.html

At minimum, you'll want to allow md5 passwords to be used over the
local network connections.

As the *root* user, edit /var/lib/pgsql/9.3/data/pg_hba.conf:
::
 # IPv4 local connections:
 host    all             all             127.0.0.1/32            md5
 # IPv6 local connections:
 host    all             all             ::1/128                 md5

NOTE Make sure to read and understand the pg_hba.conf documentation before
running a production server.

Create a superuser for your account (substitute your username for $USER):
As the *postgres* user:
::
  createuser -s $USER
  psql -c "ALTER USER $USER WITH ENCRYPTED PASSWORD 'aPassword'"

Restart PostgreSQL
As the *root* user:
::
  service postgresql-9.3 restart


Restart PostgreSQL to activate config changes, if the above was changed

As the *root* user:
::
  service postgresql-9.3 restart

Now continue in the install docs, starting from: :ref:`gitclone-chapter`

.. _gitclone-chapter:

Download and install Socorro
````````````

Clone from github
::
  git clone https://github.com/mozilla/socorro

By default, you will be tracking the latest development release. If you would
like to use a stable release, determine latest release tag from our release:
https://github.com/mozilla/socorro/releases
::
  git checkout $LATEST_RELEASE_TAG

.. _settingupenv-chapter:

Setting up environment and running dev servers
````````````
To setup Socorro, use the ``./bin/socorro setup`` command.
This will first examine your install and perform any necessary setup:
::
  $ ./bin/socorro setup --clean
  Removing virtualenvs
  Setting up virtualenv
  Setting up webapp-django
  Checking PostgreSQL
  Setting up new DB
  Generating synthetic test data ("fakedata")
  Checking RabbitMQ
  Checking ElasticSearch

Subsequent runs should detect and skip the parts that are already set up,
unless the ``--clean`` flag is supplied.

To run Socorro, use the ``./bin/socorro run`` command:
::
  $ ./bin/socorro run
  Running servers in dev mode
  Running webapp-django in dev mode
  (...)
  http://127.0.0.1:8882/
  http://127.0.0.1:8883/
  Validating models...

  0 errors found
  Django version 1.4.8, using settings 'crashstats.settings'
  Development server is running at http://127.0.0.1:8000/

You should now be able to browse the django web UI:
http://127.0.0.1:8000/

Collector accepts breakpad crashes via HTTP multi-part form POST:
http://127.0.0.1:8882/submit

The Middleware REST service (used by the django app) is on port 8883

To change the IP address, use the ``--ip_address`` flag:
::
  ./bin/socorro run --ip_address=10.11.12.13

.. _systemtest-chapter:

System Test
````````````

If you already have crash data available and wish to submit it, you can
use the standalone submitter tool. There is a test crash already loaded in
the ./testcrash/raw directory:
::
  ./bin/socorro submitter -u http://127.0.0.1:8882/submit -s ./testcrash/raw/

You should get a "CrashID" returned, for example:
::
  2013-11-11 07:13:35,704 DEBUG - Thread-1 - submission response: CrashID=bp-c6559c15-de97-4880-89ba-5744a2131108

If the crash is processed successfully, you should see the server log something
like the following:
::
  2013-11-11 07:13:38,516 INFO - CP Server Thread-1 - c6559c15-de97-4880-89ba-5744a2131108 received
  2013-11-11 07:13:39,414 INFO - CP Server Thread-1 - c6559c15-de97-4880-89ba-5744a2131108 accepted
  ::1:55213 - - [11/Nov/2013 07:13:39] "HTTP/1.1 POST /submit" - 200 OK
  2013-11-11 07:13:39,500 INFO - Thread-1 - starting job: c6559c15-de97-4880-89ba-5744a2131108
  2013-11-11 07:13:39,638 INFO - Thread-1 - finishing successful job: c6559c15-de97-4880-89ba-5744a2131108

Attempt to pull up the newly inserted crash: http://127.0.0.1:8000/report/index/c6559c15-de97-4880-89ba-5744a2131108

To generate your own test crashes:

1) Install http://code.google.com/p/crashme/ add-on for Firefox
2) Point your Firefox install at http://127.0.0.1:8882/submit

See: https://developer.mozilla.org/en/Environment_variables_affecting_crash_reporting

.. _prodinstall-chapter:

Production install (RHEL/CentOS)
````````````

The only supported production configuration for Socorro right now is
RHEL (CentOS or other clones should work as well) but it should be
fairly straightforward to get going on any OS or Linux distribution,
assuming you know how to add users, install services and get WSGI running
in your web server (we recommend Apache with mod_wsgi at this time).

Install production dependencies
````````````

As the *root* user:
::
  yum install httpd mod_wsgi memcached daemonize mod_ssl

Automatically run Apache and Memcached on startup

As the *root* user:
::
  chkconfig httpd on
  chkconfig memcached on

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

Ensure that the user doing installs owns the install dir:
::
  su -c "chown $USER /data/socorro"

Install socorro
````````````
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
````````````
From inside the Socorro checkout, as the *root* user
::
  cp config/*.ini-dist /etc/socorro

Make sure the copy each *.ini-dist file to *.ini and configure it.

It is highly recommended that you customize the files
to change default passwords, and include the common_*.ini files
rather than specifying the default password in each config file.

Install Socorro cron job manager
````````````
Socorro's cron jobs are managed by :ref:`crontabber-chapter`.

:ref:`crontabber-chapter` runs every 5 minutes from the system crontab.

Socorro ships an RC file, intended for use by cron jobs. This contains
common configuration like the path to the Socorro install, and some
convenience functions.

From inside the Socorro checkout, as the *root* user
::
  cp scripts/crons/socorrorc /etc/socorro/

edit /etc/cron.d/socorro
::
  */5 * * * * socorro /data/socorro/application/scripts/crons/crontabber.sh


Start daemons
````````````


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
````````````
Socorro requires three web services. If you are using Apache, the recommended
configuration is to run these on separate subdomains as Apache Virtual Hosts:

* crash-stats   - the web UI for viewing crash reports (Django)
* socorro-api   - the "middleware" used by the web UI
* crash-reports - the "collector" receives reports from crashing clients via HTTP POST

Ensure that crash-stats is pointing to the local socorro-api server, and
also that dev/debug/etc. options are disabled.
edit /data/socorro/webapp-django/crashstats/settings/local.py:
::
  MWARE_BASE_URL = 'http://localhost/bpapi'
  MWARE_HTTP_HOST = 'socorro-api'
  DATABASES = {
    # adjust the postgres example for your install
  }
  DEBUG = TEMPLATE_DEBUG = False
  DEV = False
  COMPRESS_OFFLINE = True
  SECRET_KEY = '' # set this to something unique

Allow Django to create the database tables it needs for managing sessions:
::
  /data/socorro/webapp-django/manage.py syncdb --noinput

Copy the example Apache config into place from the Socorro checkout as the
*root* user:
::
  cp config/apache.conf-dist /etc/httpd/conf.d/socorro.conf

Make sure to customize /etc/httpd/conf.d/socorro.conf and restart Apache when
finished, as the *root* user:
::
  service httpd restart

Troubleshooting
````````````
Socorro leaves logs in /var/log/socorro which is a good place to check
for crontabber and backend services like processor.

Socorro supports syslog and raven for application-level logging of all
services (including web services).

If web services are not starting up, /var/log/httpd is a good place to look.
