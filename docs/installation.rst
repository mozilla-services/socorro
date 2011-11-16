.. index:: installation

.. _installation-chapter:

Installation
============

Requirements:
------------
* Linux (tested on Ubuntu Lucid and RHEL/CentOS 6)

* HBase (Cloudera CDH3)

* PostgreSQL 9.0

* Python 2.6


Socorro VM (built with Vagrant + Puppet)
------------

You can build a standalone Socorro development VM -
see https://github.com/rhelmer/socorro-vagrant/ for more info. 

The config files and puppet manifests in vagrant/ can be a useful reference
when setting up Socorro for the first time, too.

Ubuntu
------------
1) Add PostgreSQL 9.0 PPA from https://launchpad.net/~pitti/+archive/postgresql
2) Add Cloudera apt source from https://ccp.cloudera.com/display/CDHDOC/CDH3+Installation#CDH3Installation-InstallingCDH3onUbuntuSystems
3) Install dependencies using apt-get

As *root*:
::
  apt-get install supervisor rsyslog libcurl4-openssl-dev build-essential sun-java6-jdk ant python-software-properties subversion libpq-dev python-virtualenv python-dev libcrypt-ssleay-perl phpunit php5-tidy python-psycopg2 python-simplejson apache2 libapache2-mod-wsgi memcached php5-pgsql php5-curl php5-dev php-pear php5-common php5-cli php5-memcache php5 php5-gd php5-mysql php5-ldap hadoop-hbase hadoop-hbase-master hadoop-hbase-thrift curl liblzo2-dev postgresql-9.0 postgresql-plperl-9.0 postgresql-contrib

RHEL/Centos
------------
Use "text install"
Choose "minimal" as install option.

1) Add Cloudera yum repo from https://ccp.cloudera.com/display/CDHDOC/CDH3+Installation#CDH3Installation-InstallingCDH3onRedHatSystems
2) Add PostgreSQL 9.0 yum repo from http://www.postgresql.org/download/linux#yum
3) Install Sun Java JDK version JDK 6u16 - Download appropriate package from http://www.oracle.com/technetwork/java/javase/downloads/index.html
4) Install dependencies using YUM:

As *root*:
::
  yum install python-psycopg2 simplejson httpd mod_ssl mod_wsgi postgresql-server postgresql-plperl perl-pgsql_perl5 postgresql-contrib subversion make rsync php-pecl-memcache memcached php-pgsql subversion gcc-c++ curl-devel ant python-virtualenv php-phpunit-PHPUnit hadoop-0.20 hadoop-hbase

5) Disable SELinux

As *root*:
  Edit /etc/sysconfig/selinux and set "SELINUX=disabled"

6) Reboot

As *root*:
::
  shutdown -r now

PostgreSQL Config
------------
RHEL/CentOS - Initialize and enable on startup (not needed for Ubuntu)

As *root*:
::
  service postgresql initdb
  service postgresql start
  chkconfig postgresql on

As *root*:

* edit /var/lib/pgsql/data/pg_hba.conf and change IPv4/IPv6 connection from "ident" to "md5"
* edit /var/lib/pgsql/data/postgresql.conf and uncomment # listen_addresses = 'localhost'
* create databases

As the *postgres* user:
::
  su - postgres
  psql
  postgres=# CREATE DATABASE breakpad;
  CREATE DATABASE
  # note - set this to something random!
  postgres=# CREATE USER breakpad_rw WITH PASSWORD 'secret';
  CREATE ROLE
  postgres=# GRANT ALL ON DATABASE breakpad TO breakpad_rw;
  GRANT
  postgres=# \c breakpad
  You are now connected to database "breakpad".
  breakpad=# CREATE LANGUAGE plpgsql;
  CREATE LANGUAGE
  breakpad=# CREATE LANGUAGE plperl;
  CREATE LANGUAGE
  postgres=# CREATE DATABASE test;
  CREATE DATABASE
  postgres=# CREATE USER test WITH PASSWORD 'aPassword';
  CREATE ROLE
  postgres=# GRANT ALL ON DATABASE test TO test;
  GRANT
  postgres=# \c test
  You are now connected to database "test".
  test=# CREATE LANGUAGE plpgsql;
  CREATE LANGUAGE
  test=# CREATE LANGUAGE plperl;
  CREATE LANGUAGE
  test=# \q
  psql -d test -f /usr/share/pgsql/contrib/citext.sql
  psql -d breakpad -f /usr/share/pgsql/contrib/citext.sql

Download and install Socorro
------------
Clone from github, as the *socorro* user:
::
  git clone https://github.com/mozilla/socorro
  cd socorro
  cp scripts/config/commonconfig.py.dist scripts/config/commonconfig.py

Edit scripts/config/commonconfig.py

From inside the Socorro checkout, as the *socorro* user, change:
::
  databaseName.default = 'breakpad'
  databaseUserName.default = 'breakpad_rw'
  databasePassword.default = 'secret'

Load PostgreSQL Schema
------------
From inside the Socorro checkout, as the *socorro* user:
::
  cp scripts/config/setupdatabaseconfig.py.dist scripts/config/setupdatabaseconfig.py
  export PYTHONPATH=.:thirdparty
  export PGPASSWORD="aPassword"
  psql -h localhost -U postgres -f scripts/schema/2.2/breakpad_roles.sql
  psql -h localhost -U postgres breakpad -f scripts/schema/2.2/breakpad_schema.sql
  cp scripts/config/createpartitionsconfig.py.dist scripts/config/createpartitionsconfig.py
  python scripts/createPartitions.py

Run unit/functional tests, and generate report
------------
From inside the Socorro checkout, as the *socorro* user:
::
  make coverage

Set up directories and permissions
------------
As *root*:
::
  mkdir /etc/socorro
  mkdir /var/log/socorro
  mkdir -p /data/socorro
  useradd socorro
  chown socorro:socorro /var/log/socorro
  mkdir /home/socorro/primaryCrashStore /home/socorro/fallback
  chown apache /home/socorro/primaryCrashStore /home/socorro/fallback
  chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback

Note - use www-data instead of apache for debian/ubuntu

Compile minidump_stackwalk

From inside the Socorro checkout, as the *socorro* user:
::
  make minidump_stackwalk

Install socorro
------------
From inside the Socorro checkout, as the *socorro* user:
::
  make install

Configure Socorro 
------------
* Start configuration with :ref:`commonconfig-chapter`
* On the machine(s) to run collector, setup :ref:`collector-chapter`
* On the machine to run monitor, setup :ref:`monitor-chapter`
* On same machine that runs monitor, setup :ref:`deferredcleanup-chapter`
* On the machine(s) to run processor, setup :ref:`processor-chapter`

Install startup scripts
RHEL/CentOS only (Ubuntu TODO - see vagrant/ for supervisord example)
------------
As *root*:
::
    ln -s /data/socorro/application/scripts/init.d/socorro-{monitor,processor,crashmover} /etc/init.d/
    chkconfig socorro-monitor on
    chkconfig socorro-processor on
    chkconfig socorro-crashmover on
    service httpd restart
    chkconfig httpd on
    service memcached restart
    chkconfig memcached on

Install Socorro cron jobs
------------
As *root*:
::
  ln -s /data/socorro/application/scripts/crons/socorrorc /etc/socorro/
  crontab /data/socorro/application/scripts/crons/example.crontab

Configure Apache
------------
As *root*:
::
  edit /etc/httpd/conf.d/socorro.conf
  cp config/socorro.conf /etc/httpd/conf.d/socorro.conf
  mkdir /var/log/httpd/{crash-stats,crash-reports,socorro-api}.example.com
  chown apache /data/socorro/htdocs/application/logs/

Note - use www-data instead of apache for debian/ubuntu

Enable PHP short_open_tag:
------------
As *root*:

edit /etc/php.ini and make the following changes:
::
  short_open_tag = On
  date.timezone = 'America/Los_Angeles'

Configure Kohana (PHP/web UI)
------------
Refer to :ref:`uiinstallation-chapter` (deprecated as of 2.2, new docs TODO)

As *root*:

edit /data/socorro/htdocs/application/config/`*`.php and customize

Hadoop+HBase install
------------
Configure Hadoop 0.20 + HBase 0.89
  Refer to https://ccp.cloudera.com/display/CDHDOC/HBase+Installation

Note - you can start with a standalone setup, but read all of the above for info on a real, distributed setup!

RHEL/CentOS only (not needed for Ubuntu)
Install startup scripts

As *root*:
::
  service hadoop-hbase-master start
  chkconfig hadoop-hbase-master on
  service hadoop-hbase-thrift start
  chkconfig hadoop-hbase-thrift on

Load Hbase schema
------------
FIXME this skips LZO suport, remove the "sed" command if you have it installed

From inside the Socorro checkout, as the *socorro* user:
::
  cat analysis/hbase_schema | sed 's/LZO/NONE/g' | hbase shell

System Test
------------
Generate a test crash:

1) Install http://code.google.com/p/crashme/ add-on for Firefox
2) Point your Firefox install at http://crash-reports/submit

See: https://developer.mozilla.org/en/Environment_variables_affecting_crash_reporting

If you already have a crash available and wish to submit it, you can
use the standalone submitter tool:

From inside the Socorro checkout, as the *socorro* user:
::
  virtualenv socorro-virtualenv
  . socorro-virtualenv/bin/activate
  pip install poster
  cp scripts/config/submitterconfig.py.dist scripts/config/submitterconfig.py
  export PYTHONPATH=.:thirdparty
  python scripts/submitter.py -u https://crash-reports-dev.allizom.org/submit -j ~/Downloads/1c11af84-3fb7-4196-a864-cf0622110911.json -d ~/Downloads/1c11af84-3fb7-4196-a864-cf0622110911.dump
 
Check syslog logs for user.*, should see the CrashID returned being collected

Attempt to pull up the newly inserted crash: https://crash-stats/report/index/0f3f3360-40a6-4188-8659-b2a5c2110808

The (syslog "user" facility) logs should show this new crash being inserted for priority processing, and it should be available shortly thereafter.

Known Issues
------------
* aggregate reports (top crashers, etc) do not work without existing data https://bugzilla.mozilla.org/show_bug.cgi?id=698943

