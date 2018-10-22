===========================
Data flow: Bug associations
===========================

Summary
=======

Bugs in Bugzilla can store which Socorro crash signatures are relevant to that
bug. Socorro keeps a cache of that data to show in various webapp views.

.. graphviz::

   digraph G {
     rankdir=LR;
     splines=lines;

     subgraph webapp {
       rank=same;
       bugsapi [shape=rect, label="Bugs API"];
       signaturesbybugsapi [shape=rect, label="SignaturesByBugs API"];
       reportview [shape=tab, label="report view"];
       topcrashersreport [shape=tab, label="topcrashers report"];
       signaturereport [shape=tab, label="signature report"];
       exploitabilityreport [shape=tab, label="exploitability report"];
     }

     bugzilla [shape=rect, label="BugzillaCronApp"];
     model [shape=box3d, label="crashstats_bugassociation"];

     bugzilla -> model [label="produces"];
     model -> bugsapi [label="used by"];
     model -> signaturesbybugsapi [label="used by"];
     model -> reportview [label="used by"];
     model -> topcrashersreport [label="used by"];
     model -> signaturereport [label="used by"];
     model -> exploitabilityreport [label="used by"];
   }


Tables
======

The data is stored in the ``crashstats.BugAssociation`` Django model and stored
in the ``crashstats_bugassociation`` PostgreSQL table.


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
