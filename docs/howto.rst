======
How to
======

Run security checks for dependencies
====================================

You can run Django command that checks for security vulnerabilities locally:

::

   $ make shell
   app@socorro:app/$ socorro-cmd depcheck


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
In ``my.env``, set ``SOCORRO_REPROCESS_API_TOKEN`` to the token value.

For example, this reprocesses a single crash::

    $ make shell
    app@socorro:app$ socorro-cmd reprocess c2815fd1-e87b-45e9-9630-765060180110

When reprocessing many crashes, it is useful to collect crashids and then
reprocess them. They are submitted in chunks, and if the script fails due
to a network error, you can edit the collected crashids to start from the
failure.

This reprocesses 100 crashes with a specified signature::

    $ make shell
    app@socorro:app$ socorro-cmd fetch_crashids --signature="some | signature" > crashids
    app@socorro:app$ cat crashids | socorro-cmd reprocess

For more complex crash sets, pass a search URL to generate the list::

    $ make shell
    app@socorro:app$ socorro-cmd fetch_crashids --num=all --url="https://crash-stats.mozilla.org/search/?product=Sample&date=%3E%3D2019-05-07T22%3A00%3A00.000Z&date=%3C2019-05-07T23%3A00%3A00.000Z" > crashids
    app@socorro:app$ cat crashids | socorro-cmd reprocess

