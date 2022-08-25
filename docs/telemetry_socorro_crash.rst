.. _telemetry-chapter:

===================================
Telemetry (telemetry.socorro_crash)
===================================

Socorro exports specific crash report data to Telemetry. This data is in the
``telemetry.socorro_crash`` data set.


Querying telemetry.socorro_crash data
=====================================

Please see the `telemetry.socorro_crash documentation
<https://docs.telemetry.mozilla.org/datasets/other/socorro_crash/reference.html>`_.


Adding fields to telemetry.socorro_crash
========================================

`File a bug <https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&component=General&op_sys=All&product=Socorro&rep_platform=All&short_desc=please%20add%20FIELDNAME%20to%20telemetry.socorro_crash>`_
to add new fields to ``telemetry.socorro_crash``.

If the crash report annotations and haven't been documented, then we may ask
you to document them before we proceed. See :ref:`annotations-chapter` for
details.


Things to know
==============

1. The data in ``telemetry.socorro_crash`` comes from the first time a crash
   report is processed. If a crash report is re-processed, the changes will not
   be reflected in ``telemetry.socorro_crash``.

2. Fields can only be added to ``telemetry.socorro_crash``--they can't be
   changed.

3. Only fields that contain non-sensitive data can be added to the schema.

4. When new fields are added, data cannot be backfilled.

5. If the crash report annotation value doesn't conform to the schema, it will
   either get dropped or result in the entire crash report getting dropped.

6. Crash report data is ingested into Telemetry in a batch job that runs once a
   day. The ``telemetry.socorro_crash`` data set lags behind what you see on
   Crash Stats website.
