=========
Platforms
=========

Summary
=======

The webapp maintains a list of platforms.

.. graphviz::

   digraph G {
     rankdir=LR;
     splines=lines;

     subgraph webapp {
       rank=same;

       topcrashers [shape=tab, label="topcrashers report"];
       supersearch [shape=tab, label="supersearch"];
     }

     adminpage [shape=tab, label="admin"];
     model [shape=box3d, label="crashstats_platform"];

     adminpage -> model [label="produces"];
     model -> topcrashers [label="uses"];
     model -> supersearch [label="uses"];
   }


Tables
======

The data is stored in the ``crashstats.Platform`` Django model. This is the
``crashstats_platform`` table in PostgreSQL.


Where the data comes from
=========================

The data is maintained by a Django admin page.


What uses this data
===================

Pages in the webapp that use this data:

* supersearch
* topcrashers report
