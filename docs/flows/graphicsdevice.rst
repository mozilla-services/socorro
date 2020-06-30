================
Graphics devices
================

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

Data is added to the table manually using the Crash Stats Django admin.

1. Log into Crash Stats.
2. Go to the admin.
3. Click on Management Pages -> Graphics Devices
4. Upload a new file from `PCI ID repository <https://pci-ids.ucw.cz/>`_.

The function for parsing that file is `pci_ids__parse_graphics_device_iterable`
at:

https://github.com/mozilla-services/socorro/blob/main/webapp-django/crashstats/manage/utils.py#L21


What uses this data
===================

Pages in the webapp that use this data:

* report view
* signature summary

They convert the hex codes in the crash reports to human-friendly labels
in the table.
