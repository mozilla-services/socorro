======
How to
======

Run security checks for dependencies
====================================

You can run the crontabber job that checks for security vulnerabilities locally:

::

   make dependencycheck


Connect to PostgreSQL Database in local dev environment
=======================================================

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
    app@processor:app$ socorro-cmd reprocess c2815fd1-e87b-45e9-9630-765060180110

This reprocesses crashes all crashes with a specified signature::

    $ docker-compose run processor bash
    app@processor:app$ socorro-cmd fetch_crashids --signature="some | signature" | socorro-cmd reprocess
