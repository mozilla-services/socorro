.. index:: setupdevenv

.. _setupdevenv-chapter:

Setup a development environment
===============================

The best and easiest way to get started with a complete dev environment is to
use Vagrant and our installation script. You can find all the instructions
here: https://github.com/rhelmer/socorro-vagrant

If you don't want to use a virtual machine, you can install everything in your
own development environment. All steps are described in
:ref:`standalone-chapter`.

Use your own git repo
---------------------

If you forked our mozilla/socorro repository, you will want to make your repo
the origin of the repository inside your VM. Once connected through SSH into
the VM, execute the following commands::

    sudo su - socorro
    cd /home/socorro/dev/socorro
    edit .git/config # change `url = git@github.com:mozilla/socorro.git` with your repo's URL
    git fetch origin

.. _applychanges-label:

Apply your changes
------------------

After that, whenever you want to see changes you made in one of your branches,
do the following::

    cd /home/socorro/dev/socorro
    git checkout my-dev-branch
    make install
    sudo /etc/init.d/apache2 restart
    sudo /etc/init.d/supervisor force-stop && sudo /etc/init.d/supervisor start

And then from your browser access http://crash-stats/ for the UI, or
http://socorro-api/bpapi/ for the middleware API directly.

Use a shared folder
-------------------

If you don't like vim or you want to use your favorite IDE, you can easily
create a shared folder between your OS and your VM. You can then work in your
OS and have all your changes automatically passed to the VM.

The best solution is to use NFS. There is good documentation on the Vagrant
website that explains it all: http://vagrantup.com/docs/nfs.html


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
