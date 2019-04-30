====================
Data flow: Signature
====================

Summary
=======

Socorro keeps track of the first time it saw a signature and the first build it
saw a signature.


.. graphviz::

   digraph G {
     rankdir=LR;
     splines=lines;

     subgraph webapp {
       signaturefirstdateapi [shape=rect, label="SignatureFirstDate API"];
       topcrashersreport [shape=tab, label="topcrashers report"];
     }

     updatesignatures [shape=rect, label="updatesignatures"];
     model [shape=box3d, label="crashstats_bugassociation"];

     updatesignatures -> model [label="produces"];
     model -> signaturefirstdateapi [label="used by"];
     model -> topcrashersreport [label="used by"];
   }


Tables
======

The data is stored in the ``crashstats.Signature`` Django model and stored
in the ``crashstats_signature`` PostgreSQL table.


Where the data comes from
=========================

The ``updatesignatures`` Django command looks at all the crash reports in
Elasticsearch for some period of time, then goes through and updates the
``first_build`` and ``first_date`` columns.


What uses the data
==================

Pages in the webapp that use this data:

* topcrashers report
* ``SignatureFirstDate`` API endpoint
