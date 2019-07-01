======
How to
======

.. contents::

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


Reprocessing lots of crashes if you are not an admin
----------------------------------------------------

If you need to reprocess a lot of crashes, please `write up a bug
<https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&comment=DESCRIBE%20WHAT%20YOU%20WANT%20REPROCESSED%20HERE&component=General&form_name=enter_bug&product=Socorro&short_desc=reprocess%20request%3A%20SUMMARY>`_.
In the bug description, include a Super Search url with the crashes you want
reprocessed.


Reprocessing crashes if you are an admin
----------------------------------------

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


Processing requests for PII access
==================================

People file bugs in Bugzilla asking to be granted access to PII using
`these instructions <https://crash-stats.mozilla.org/documentation/memory_dump_access/>`_.

Process for handling those:

1. Check to see if they're a Mozilla employee. If they aren't, then we can't
   grant them access.

2. Make sure they've logged into Crash Stats prod. If they have, there will be a
   user account with their LDAP username.

3. Look them up in phonebook and find their manager.

4. Reply in the bug asking the reporter to agree to the memory dump access
   agreement. Make sure to copy and paste the terms in the bug comments as well
   as the url to where it exists. Tag the reporter with a needinfo.

5. Reply in the bug asking the manager to verify the reporter requires access to
   PII on Crash Stats for their job. Tag the manager with a needinfo.

Then wait for those needinfos to be filled. Once that's done:

1. Log into Crash Stats.
2. Go into the admin.
3. Look up the user.
4. Add the user to the "Hackers" group.

Then reply in the bug something like this::

    You have access to PII on Crash Stats. You might have to log out and log
    back in again. Let us know if you have any problems!

    Thank you!

and mark the bug FIXED.

That's it!
