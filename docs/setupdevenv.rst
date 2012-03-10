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

To get started with Vagrant, simply update the vagrant submodule from your local git checkout::

    git submodule update --init vagrant
    cd vagrant/

Check out the README in that directory to get started.

Apply your changes
------------------
By default, your socorro git checkout will be shared into the VM via NFS
at /home/socorro/dev/socorro

To actually make changes take effect, you can run::

    vagrant provision

This reruns puppet inside the VM to deploy the source to /data/socorro and 
restarts any necessary services.

And then from your browser access http://crash-stats/ for the UI, or
http://socorro-api/bpapi/ for the middleware API directly.

Setting up a new database
----------------
If you do not have an existing production database to import, or wish to
create a new standalone database for testing, see :ref:`populatepostgres-chapter`
or :ref:`populateelasticsearch-chapter`.

Pulling crash reports from production
----------------
The Socorro PostgreSQL database only contains a small subset of the information
about individual crashes (enough to run aggregate reports). For instance the
full stack is only available in long-term storage (such as HBase).

If you have imported a database from a production instance, you may want
to configure the web UI to pull individual crash reports from production via
the web service (so URLs such as https://crash-stats.mozilla.com/report/index/0f3f3360-40a6-4188-8659-b2a5c2110808 will work).

The /report/index page actually pulls it's data from a URL such as:
https://crash-stats.mozilla.com/dumps/0f3f3360-40a6-4188-8659-b2a5c2110808.jsonz

You can cause your dev instance to fall back to your production instance by
modifying:
::
  webapp-php/application/config/application.php

Change the URL in this config value to point to your desired production instance:

.. code-block:: php

  <?php
  $config['crash_dump_local_url_fallback'] = 'https://crash-stats.mozilla.com/dumps/%1$s.jsonz';
  ?>

Note that the crash ID must be in both your local database and the remote
(production) HBase instance for this to work.

See https://github.com/mozilla/socorro/blob/master/webapp-php/application/config/application.php-dist
