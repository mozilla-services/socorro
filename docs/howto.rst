======
How to
======

Run security checks for dependencies
====================================

You can run the crontabber job that checks for security vulnerabilities locally:

::

   make dockerdependencycheck


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
