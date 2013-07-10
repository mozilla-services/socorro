.. index:: vagrant

.. _vagrant-chapter:

Setup a development VM with Vagrant
===============================

Vagrant can be used to build a full Socorro VM.

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
Note that the existing puppet manifests populate PostgreSQL if the "breakpad"
database does not exist. See :ref:`fakedata-chapter` for more information on
how this process works, and how to customize it.

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


Apache logs Django webapp errors, and may log other errors such as WSGI apps not starting up or
problems with the Apache configs:
::
  /var/log/apache/error.log

All other Socorro apps log to syslog, using the user.* facility:
::
  /var/log/user.log

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

(OPTIONAL) Populating Elastic Search
----------------
See :ref:`populateelasticsearch-chapter`.
