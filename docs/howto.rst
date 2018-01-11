======
How to
======

Run security checks for dependencies
====================================

You can run the crontabber job that checks for security vulnerabilities locally:

::

   make dockerdependencycheck


Connect to PostgreSQL Database
==============================

The local development environment's PostgreSQL database exposes itself on a
non-standard port when run with docker-compose. You can connect to it with
the client of your choice using the following connection settings:

* Username: ``postgres``
* Password: ``aPassword``
* Port: ``8574``


Reprocess crashes
=================

Reprocessing individual crashes
-------------------------------

If you have appropriate permissions, you can reprocess an individual crash by
viewing the crash report on the Crash Stats site, clicking on the "Reprocess"
tab, and clicking on the "Reprocess this crash" button.


Reprocessing lots of crashes if you're not an admin
---------------------------------------------------

If you need to reprocess a lot of crashes, please `write up a bug
<https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro>`_.
In the bug description, include a Super Search url with the crashes you want
reprocessed.


Reprocessing crashes if you're an admin
---------------------------------------

If you're an admin, you can create an API token with the "Reprocess Crashes"
permission. You can use this token in conjunction with the
``scripts/reprocess.py`` script to set crashes up for reprocessing.

For example, this reprocesses a single crash::

    $ docker-compose run processor bash
    app@processor:app$ ./scripts/reprocess.py c2815fd1-e87b-45e9-9630-765060180110

This reprocesses crashes all crashes with a specified signature::

    $ docker-compose run processor bash
    app@processor:app$ ./scripts/fetch_crashids.py --signature="some | signature" | ./scripts/reprocess.py


.. Warning::

   If you're reprocessing more than 10,000 crashes, make sure to add a sleep
   argument of 10 seconds (``--sleep 10``). This will slow down adding items to
   the reprocessing queue such that the rate of crashes being added is roughly
   the rate of crashes being processed. Otherwise, you'll exceed our alert
   triggers for queue sizes and it'll page people.


.. Warning::

   August 17th, 2017: Everything below this point is outdated.


Populate PostgreSQL Database
============================

Load Socorro schema plus test products:

::

   socorro setupdb --database_name=breakpad --createdb


Create partitioned tables
=========================

Normally this is handled automatically by the cronjob scheduler
:ref:`crontabber-chapter` but can be run as a one-off:

::

   python socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force


Populate Elasticsearch database
===============================

.. Note::

   See the chapter about :ref:`elasticsearch-chapter` for more information.

Once you have populated your PostgreSQL database with "fake data",
you can migrate that data into Elasticsearch:

::

   python socorro/external/postgresql/crash_migration_app.py


Sync Django database
====================

Django needs to write its ORM tables:

::

   export SECRET_KEY="..."
   cd webapp-django
   ./manage.py migrate auth
   ./manage.py migrate


Adding new products and releases
================================

Each product you wish to have reports on must be added via the Socorro
admin UI:

http://crash-stats/admin/products/

All products must have one or more releases:

http://crash-stats/admin/releases/

Make sure to restart memcached so you see your changes right away:

::

    sudo systemctl restart memcached


Now go to the front page for your application. For example, if your application
was named "KillerApp" then it will appear at:

http://crash-stats/home/products/KillerApp
