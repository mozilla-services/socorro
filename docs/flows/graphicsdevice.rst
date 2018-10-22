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


Tables
======

The data is stored in the ``crashstats.GraphicsDevice`` Django model.


Where the data comes from
=========================

Data is added to the table manually using the Crash Stats Django admin. See the
admin page for details.


What uses this data
===================

Pages in the webapp that use this data:

* report view
* signature summary
