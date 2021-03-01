================
Graphics devices
================

Summary
=======

Crash reports come in with a ``AdapterVendorID`` and ``AdapterDeviceID`` crash
annotations. These are hex codes in the form of ``0xNNNN``. The webapp has a
lookup table to convert the hex codes into friendly names.

This data is hierarchical. Vendor hex codes are unique. Each vendor has many
devices each with a device hex code. Device hex codes aren't unique across
multiple vendors.

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

Data is added to the table automatically using the ``update_graphics_pci`` cron
job. This job runs once a week to pick up new device ids.

The function for parsing that file is `pci_ids__parse_graphics_device_iterable`
in ``webapp-django/crashstats/crashstats/utils.py``.

If you need to, you can edit the table data directly using the Django admin.


What uses this data
===================

Pages in the webapp that use this data:

* report view
* signature summary

They convert the hex codes in the crash reports to human-friendly labels
in the table.
