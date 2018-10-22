===========================
Data flow: Graphics devices
===========================

Summary
=======

Crash reports come in with a Vendor Hex and an Adapter Hex. The webapp stores
a lookup table to convert these codes into friendly names.

This data is hierarchical. Vendor Hex codes are unique. Each vendor has many
adapters each with its own Adapter Hex code. Adapter Hex codes aren't unique
across multiple vendors.

.. graphviz::

   digraph G {
     rankdir=LR;
     splines=lines;

     subgraph webapp {
       rank=same;
       reportview [shape=tab, label="report view"];
       signatureview [shape=tab, label="signature summary"];
     }

     adminpage [shape=tab, label="admin"];
     model [shape=box3d, label="crashstats_graphicsdevice"];

     adminpage -> model [label="produces"];
     model -> reportview [label="used by"];
     model -> signatureview [label="used by"];
   }


Tables
======

The data is stored in the ``crashstats.GraphicsDevice`` Django model. This is the
``crashstats_graphicsdevice`` table in PostgreSQL.


Where the data comes from
=========================

Data is added to the table manually using the Crash Stats Django admin. See the
admin page for details.


What uses this data
===================

Pages in the webapp that use this data:

* report view
* signature summary
