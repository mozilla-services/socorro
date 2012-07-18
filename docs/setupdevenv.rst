.. index:: setupdevenv

.. _setupdevenv-chapter:

Setup a development environment
===============================

The best and easiest way to get started with a complete dev environment is to
use Vagrant and our installation script. 

.. sidebar:: Standalone dev environment in your existing environment

    If you don't want to do things the easy way, or can't use a virtual machine,
    you can install everything in your own development environment. All steps 
    are described in :ref:`standalone-chapter`.

1. Clone Socorro repository
::
  git clone git://github.com/mozilla/socorro.git
  cd socorro/

2. Install VirtualBox from:
http://www.virtualbox.org/

3. Install Vagrant from:
http://vagrantup.com/

4. Download base box
::
 # NOTE: if you have a 32-bit host, change "lucid64" to "lucid32"
 vagrant box add socorro-all http://files.vagrantup.com/lucid64.box

5. Copy base box, boot VM and provision it with puppet:
::
 vagrant up

6. Add to /etc/hosts (on the HOST machine!):
::
  33.33.33.10 crash-stats crash-reports socorro-api

Enjoy your Socorro environment!
  * browse UI: 
    http://crash-stats
  * submit crashes: 
    http://crash-reports/submit (accepts HTTP POST only, see :ref:`systemtest-chapter` for 
    information on submitting test crashes)
  * query data via middleware API:
    http://socorro-api/bpapi/adu/byday/p/WaterWolf/v/1.0/rt/any/osx/start/YYYY-MM-DD/end/YYYY-MM-DD
    (where *WaterWolf* is a valid productname and *YYYY-MM-DD* are valid start/end dates)


Apply your changes
------------------

Edit files in your git checkout on the host as usual.
To actually make changes take effect, you can run::

    vagrant provision

This reruns puppet inside the VM to deploy the source to /data/socorro and 
restarts any necessary services.

How Socorro works
----------------

See :ref:`howsocorroworks-chapter` and :ref:`crashflow-chapter`.

Setting up a new database
----------------
Note that the existing puppet manifests populate PostgreSQL if the "breakpad" database
does not exist. See :ref:`populatepostgres-chapter` for more information on how this process
works, and how to customize it.

Enabling HBase
----------------
Socorro supports HBase as a long-term storage archive for both raw and
processed crashes. Since it requires Sun (now Oracle) Java and does not 
work with OpenJDK, and generally has much higher memory requirements than
all the other dependencies, it is not enabled by default.

If you wish to enable it, edit the nodes.pp file:
::
  vi puppet/manifests/nodes/nodes.pp

And remove the comment ('#') marker from the socorro-hbase include:
::
  #    include socorro-hbase

Re-provision vagrant, and HBase will be installed, started and the default Socorro schema
will be loaded:
::
  vagrant provision

NOTE - this will download and install Java from Oracle, which means that
you will be bound by the terms of their license agreement - http://www.oracle.com/technetwork/java/javase/terms/license/

Debugging
------------------

You can SSH into your VM by running:
::
  vagrant ssh

By default, your socorro git checkout will be shared into the VM via NFS
at /home/socorro/dev/socorro

Running "make install" as socorro user in /home/socorro/dev/socorro will cause
Socorro to be installed to /data/socorro/. You will need to restart
the apache2 or supervisord services if you modify middleware or backend code, respectively
(note that "vagrant provision" as described above does all of this for you).

Logs for the (PHP Kohana) webapp are at:
::
  /data/socorro/htdocs/application/logs/

All other Socorro apps log to syslog, using the user.* facility:
::
  /var/log/user.log

Apache may log important errors too, such as WSGI apps not starting up or
problems with the Apache or PHP configs:
::
  /var/log/apache/error.log

Supervisord captures the stderr/stdout of the backend jobs, these are normally
the same as syslog but may log important errors if the daemons cannot be started.
You can also find stdout/stderr from cron jobs in this location:
::
  /var/log/socorro/

Loading data from an existing Socorro install
----------------

Given a PostgreSQL dump named "minidb.dump", run the following.
::
 vagrant ssh
 # shut down database users
 sudo /etc/init.d/supervisor force-stop
 sudo /etc/init.d/apache2 stop

 # drop old db and load snapshot
 sudo su - postgres
 dropdb breakpad
 createdb -E 'utf8' -l 'en_US.utf8' -T template0 breakpad
 pg_restore -Fc -d breakpad minidb.dump

This may take several hours, depending on your hardware. 
One way to speed this up would be to add more CPU cores to the VM (via virtualbox GUI), default is 1.

Add "-j n" to pg_restore command above, where n is number of CPU cores - 1

Pulling crash reports from an existing production install
----------------
The Socorro PostgreSQL database only contains a small subset of the information
about individual crashes (enough to run aggregate reports). For instance the
full stack is only available in long-term storage (such as HBase).

If you have imported a database from a production instance, you may want
to configure the web UI to pull individual crash reports from production via
the web service (so URLs such as http://crash-stats/report/index/YOUR_CRASH_ID_GOES_HERE will work).

The /report/index page actually pulls it's data from a URL such as:
http://crash-stats/dumps/YOUR_CRASH_ID_GOES_HERE.jsonz

You can cause your dev instance to fall back to your production instance by
modifying:
::
  webapp-php/application/config/application.php

Change the URL in this config value to point to your desired production instance:

.. code-block:: php

  <?php
  $config['crash_dump_local_url_fallback'] = 'http://crash-stats/dumps/%1$s.jsonz';
  ?>

Note that the crash ID must be in both your local database and the remote
(production) HBase instance for this to work.

See https://github.com/mozilla/socorro/blob/master/webapp-php/application/config/application.php-dist

(OPTIONAL) Populating Elastic Search
----------------
See :ref:`populateelasticsearch-chapter`.
