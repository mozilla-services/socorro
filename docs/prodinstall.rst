.. index:: prodinstall

.. _prodinstall-chapter:

Production Install
======================================

Requirements
````````````

This guide assumes that you have already followed all steps in :ref:`installation-chapter`

Ubuntu
````````````
Install dependencies
::
  sudo apt-get install supervisor rsyslog libapache2-mod-wsgi memcached

Set up directories and permissions
::
  sudo mkdir /etc/socorro
  sudo mkdir /var/log/socorro
  sudo mkdir -p /data/socorro
  sudo useradd socorro
  sudo chown socorro:socorro /var/log/socorro
  sudo mkdir /home/socorro/primaryCrashStore /home/socorro/fallback /home/socorro/persistent
  sudo chown www-data-socorro /home/socorro/primaryCrashStore /home/socorro/fallback
  sudo chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback


RHEL/Centos
````````````
Install dependencies
::
  sudo yum install httpd mod_ssl mod_wsgi memcached daemonize

Set up directories and permissions
::
  sudo mkdir /etc/socorro
  sudo mkdir /var/log/socorro
  sudo mkdir -p /data/socorro
  sudo useradd socorro
  sudo chown socorro:socorro /var/log/socorro
  sudo mkdir /home/socorro/primaryCrashStore /home/socorro/fallback /home/socorro/persistent
  sudo chown apache /home/socorro/primaryCrashStore /home/socorro/fallback
  sudo chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback


Install socorro
````````````
From inside the Socorro checkout
::
  make install

By default, this installs files to /data/socorro. You can change this by 
specifying the PREFIX:
::
  make install PREFIX=/usr/local/socorro


Install Socorro cron jobs
````````````
From inside the Socorro checkout, as the *root* user:
::
  ln -s /data/socorro/application/scripts/crons/socorrorc /etc/socorro/
  cp puppet/files/etc_crond/socorro /etc/cron.d/

Socorro's cron jobs are moving to a new cronjob manager called :ref:`crontabber-chapter`.
:ref:`crontabber-chapter` runs every 5 minutes from the system crontab,
and looks inside the config/ directory for it's configuration.

However some configuration is shared and site-specific, so is expected to
be in the system directory /etc/socorro :

From inside the Socorro checkout, as the *root* user:
::
  cp puppet/files/etc_socorro/postgres.ini /etc/socorro/

Start daemons
````````````

TODO use init scripts, supervisord etc.
Some old examples in puppet/files/etc_supervisor/

Configure Apache
````````````
Socorro uses three virtual hosts:

* crash-stats   - the web UI for viewing crash reports
* socorro-api   - the "middleware" used by the web UI 
* crash-reports - receives reports from crashing clients (via HTTP POST)

As *root*:
::
  cp puppet/files/etc_apache2_sites-available/{crash-reports,crash-stats,socorro-api} /etc/httpd/conf.d/

edit /etc/httpd/conf.d/{crash-reports,crash-stats,socorro-api} and customize
as needed for your site

As *root*
::
  mkdir /var/log/httpd/{crash-stats,crash-reports,socorro-api}.example.com
  chown apache /data/socorro/htdocs/application/logs/

Note - use www-data instead of apache for debian/ubuntu

