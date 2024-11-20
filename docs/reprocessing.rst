====================
Reprocessing crashes
====================

Reprocessing individual crashes
===============================

If you have appropriate permissions, you can reprocess an individual crash by
viewing the crash report on the Crash Stats site, clicking on the "Reprocess"
tab, and clicking on the "Reprocess this crash" button.


Reprocessing lots of crashes if you are not an admin
====================================================

If you need to reprocess a lot of crashes, please `write up a bug
<https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&comment=DESCRIBE%20WHAT%20YOU%20WANT%20REPROCESSED%20HERE&component=General&form_name=enter_bug&product=Socorro&short_desc=reprocess%20request%3A%20SUMMARY>`_.
In the bug description, include a Super Search url with the crashes you want
reprocessed.


Reprocessing crashes if you are an admin
========================================

If you're an admin, you can create an API token with the "Reprocess Crashes"
permission. You can use this token in conjunction with the
``scripts/reprocess.py`` script to set crashes up for reprocessing.
In ``my.env``, set ``SOCORRO_REPROCESS_API_TOKEN`` to the token value.

For example, this reprocesses a single crash::

    $ just shell
    app@socorro:app$ socorro-cmd reprocess c2815fd1-e87b-45e9-9630-765060180110

When reprocessing many crashes, it is useful to collect crashids and then
reprocess them. They are submitted in chunks, and if the script fails due
to a network error, you can edit the collected crashids to start from the
failure.

This reprocesses 100 crashes with a specified signature::

    $ just shell
    app@socorro:app$ socorro-cmd fetch_crashids --signature="some | signature" > crashids
    app@socorro:app$ cat crashids | socorro-cmd reprocess

For more complex crash sets, pass a search URL to generate the list::

    $ just shell
    app@socorro:app$ socorro-cmd fetch_crashids --num=all --url="https://crash-stats.mozilla.org/search/?product=Sample&date=%3E%3D2019-05-07T22%3A00%3A00.000Z&date=%3C2019-05-07T23%3A00%3A00.000Z" > crashids
    app@socorro:app$ cat crashids | socorro-cmd reprocess
