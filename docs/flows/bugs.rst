===========================
Data flow: Bug associations
===========================

Summary
=======

Bugs in Bugzilla can store which Socorro crash signatures are relevant to that
bug. Socorro keeps a cache of that data to show in various webapp views.


Tables
======

The data is stored in the ``crashstats.BugAssociation`` Django model.


Where the data comes from
=========================

The ``socorro.crontabber.jobs.bugzilla.BugzillaCronApp`` crontabber app looks at
all the bugs in Bugzilla that have been created or had their
``cf_crash_signature`` field updated for some period of time. It updates the
``bug_associations`` table with any new associations and any associations that
were removed.


What uses the data
==================

Pages in the webapp that use this data:

* ``Bugs`` API endpoint (shows bugs and related bugs)
* ``SignaturesByBugs`` API endpoint
* report view
* topcrashers report
* signature report
* exploitability report
