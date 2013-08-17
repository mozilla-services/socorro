.. index:: installation

.. _installation-chapter:

Installation
============

How Socorro Works
````````````

Socorro is a set of components for collecting, processing and reporting on crashes. It is used by Mozilla for tracking crashes of Firefox, B2G, Thunderbird and other projects. The production Mozilla install is public and hosted at https://crash-stats.mozilla.com/

The components which make up Socorro are:

* Collector - collects breakpad minidump crashes which come in over HTTP POST
* Monitor - watch for incoming crashes, feed to processor
* Processor - turn breakpad minidump crashes into stack traces and other info
* Middleware - provide HTTP REST interface for JSON reports and real-time crash data
* Web UI aka crash-stats - django-based web app for visualizing and reporting on crash data

There are two main parts to Socorro:

1) collects, processes, and allows real-time searches and results for individual crash reports

  This requires both PostgreSQL, as well as the Collector, Monitor, Processor and Middleware and Web UI.

  Individual crash reports are pulled from long-term storage using the
  /report/index/ page, for example: https://crash-stats.mozilla.com/report/index/ba8c248f-79ff-46b4-97b8-a33362121113

  The search feature is at: https://crash-stats.mozilla.com/query

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
* PostgreSQL 9.2
* Python 2.6
* C++ compiler
* Subversion
* Git
* PostrgreSQL and Python dev libraries (for psycopg2)

Mac OS X
````````````
Install dependencies
::
  brew update
  brew tap homebrew/versions
  brew install python26 git gpp postgresql subversion
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

Ubuntu 12.04 (Precise)
````````````
Install dependencies
::
  sudo apt-get update
  sudo apt-get install python-software-properties
  sudo add-apt-repository ppa:pitti/postgresql
  sudo add-apt-repository ppa:fkrull/deadsnakes
  sudo apt-get update
  sudo apt-get install build-essential subversion libpq-dev python-virtualenv python-dev postgresql-9.2 postgresql-plperl-9.2 postgresql-contrib-9.2 postgresql-server-dev-9.2 rsync python2.6 python2.6-dev libxslt1-dev git-core mercurial

Modify postgresql config
::
  sudo editor /etc/postgresql/9.2/main/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Restart PostgreSQL to activate config changes, if the above was changed
::
  sudo /usr/sbin/service postgresql restart


RHEL/CentOS 6
````````````
* Add PostgreSQL 9.2 yum repo from http://www.postgresql.org/download/linux#yum

Install [epel repository](http://fedoraproject.org/wiki/EPEL)
::
  rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm

Install dependencies
::
  sudo yum install postgresql92-server postgresql92-plperl postgresql92-contrib postgresql92-devel subversion make rsync subversion gcc-c++ python-devel python-pip mercurial git libxml2-devel libxslt-devel

Initialize and enable PostgreSQL on startup
::
  sudo service postgresql-9.2 initdb
  sudo service postgresql-9.2 start
  sudo chkconfig postgresql-9.2 on

Modify postgresql config
::
  sudo vi /var/lib/pgsql/9.2/data/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Restart PostgreSQL to activate config changes, if the above was changed
::
  sudo service postgresql-9.2 restart

Add a new superuser account to postgres
````````````

Create a superuser account for yourself
::
  sudo su - postgres -c "createuser -s $USER"

Download and install Socorro
````````````

Clone from github
::
  git clone --depth=1 https://github.com/mozilla/socorro

By default, you will be tracking the latest development release. If you would
like to use a stable release, determine latest release tag from our release tracking wiki: https://wiki.mozilla.org/Socorro:Releases#Previous_Releases
::
  git fetch origin --tags --depth=1
  git checkout $LATEST_RELEASE_TAG


Install json_extensions for use with PostgreSQL
```````````````````````````````````````````````
From inside the Socorro checkout
::
  export PATH=$PATH:/usr/pgsql-9.2/bin/
  make json_enhancements_pg_extension

Populate PostgreSQL Database
````````````
Load the Socorro schema
-------------------

Load the Socorro schema
::
  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad --dropdb --database_superusername=your_superuser --database_superuserpassword=bPassword

By default, setupdb_app.py will use 'breakpad_superuser' as the superuser, and
'bPassword' as the password. This is required because 'breakpad_rw' user must
not be a superuser in the database.

You should edit change the passwords, for a production install.
::
  psql -f sql/roles.sql breakpad

IMPORTANT NOTE - many reports use the reports_clean_done() stored
procedure to check that reports exist for the last UTC hour of the
day being processed, as a way to catch problems. If your crash
volume does not guarantee one crash per hour, you may want to modify
this function in
socorro/external/postgresql/raw_sql/procs/reports_clean_done.sql
and reload the schema
::

  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad --dropdb --database_superusername=your_superuser --database_superuserpassword=bPassword

If you want to hack on Socorro, or just see what a functional system looks
like, you also have the option to generate and populate the DB with synthetic
test data
::
  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad --fakedata --dropdb --database_superusername=your_superuser --database_superuserpassword=bPassword

Run unit/functional tests
````````````

From inside the Socorro checkout
::
  make test


Install minidump_stackwalk
````````````
This is the binary which processes breakpad crash dumps into stack traces:
::
  make minidump_stackwalk

Setting up environment
````````````
To run and hack on Socorro apps, you will need:

1) all dependencies installed from requirements/{prod,dev}.txt
1.1) also requirements/dev.txt, if you are doing development
2) set PYTHONPATH to .

Socorro can install the dependencies into a virtualenv for you, then
just activate it and set your PYTHONPATH
::
  make bootstrap-dev
  . socorro-virtualenv/bin/activate
  export PYTHONPATH=.

Or you can choose to manage the virtualenv yourself, perhaps using
virtualenwrapper or similar.

Populate PostgreSQL Database
````````````
Load the Socorro schema
-------------------

Before loading the schema, make sure to load the roles required for Socorro.
You should edit change the passwords, for a production install.
::
  psql -f sql/roles.sql postgres

Load the Socorro schema
::
  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad

IMPORTANT NOTE - many reports use the reports_clean_done() stored
procedure to check that reports exist for the last UTC hour of the
day being processed, as a way to catch problems. If your crash
volume does not guarantee one crash per hour, you may want to modify
this function in
socorro/external/postgresql/raw_sql/procs/reports_clean_done.sql
and reload the schema
::

  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad --dropdb --database_superusername=your_superuser --database_superuserpassword=bPassword

By default, setupdb_app.py will use 'breakpad_superuser' as the superuser, and
'bPassword' as the password. This is required because 'breakpad_rw' user must
not be a superuser in the database.

If you want to hack on Socorro, or just see what a functional system looks
like, you also have the option to generate and populate the DB with synthetic
test data
::
  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad --fakedata --dropdb --database_superusername=your_superuser --database_superuserpassword=bPassword


Create partitioned reports_* tables
------------------------------------------
Socorro uses PostgreSQL partitions for the reports table, which must be created
on a weekly basis.

Normally this is handled automatically by the cronjob scheduler
:ref:`crontabber-chapter` but can be run as a one-off:
::
  python socorro/cron/crontabber.py --job=weekly-reports-partitions --force

Run socorro in dev mode
````````````

Copy default config files
::
  cp config/collector.ini-dist config/collector.ini
  cp config/processor.ini-dist config/processor.ini
  cp config/monitor.ini-dist config/monitor.ini
  cp config/middleware.ini-dist config/middleware.ini

Run Socorro servers - NOTE you should use different terminals for each, perhaps in a screen session
::
  python socorro/collector/collector_app.py --admin.conf=./config/collector.ini
  python socorro/processor/processor_app.py --admin.conf=./config/processor.ini
  python socorro/monitor/monitor_app.py --admin.conf=./config/monitor.ini
  python socorro/middleware/middleware_app.py --admin.conf=config/middleware.ini

If you want to modify something that is common across config files like PostgreSQL username/hostname/etc, make sure to see config/common_database.ini-dist and the "+include" line in the service-specific config files (such as collector.ini, processor.ini and monitor.ini). This is optional but recommended.


Run webapp-django in dev mode
````````````

Install dependencies for web front end:
https://github.com/mozilla/socorro/blob/master/webapp-django/INSTALL.md

Configure webapp-django/crashstats/settings/local.py to point at
your local middleware server
::
  MWARE_BASE_URL = 'http://localhost:8883'

Production install
````````````
Refer to :ref:`prodinstall-chapter` for information about
installing Socorro for production use.

.. _systemtest-chapter:

System Test
````````````
Generate a test crash:

1) Install http://code.google.com/p/crashme/ add-on for Firefox
2) Point your Firefox install at http://crash-reports/submit

See: https://developer.mozilla.org/en/Environment_variables_affecting_crash_reporting

If you already have a crash available and wish to submit it, you can
use the standalone submitter tool (assuming the JSON and dump files for your
crash are in the "./crashes" directory)
::
  python socorro/collector/submitter_app.py -u http://crash-reports/submit -s ./crashes/

You should get a "CrashID" returned.
Check syslog logs for user.*, should see the CrashID returned being collected.

Attempt to pull up the newly inserted crash: http://crash-stats/report/index/YOUR_CRASH_ID_GOES_HERE

The (syslog "user" facility) logs should show this new crash being inserted for priority processing, and it should be available shortly thereafter.
