.. _telemetry-chapter:

===================================
Telemetry (telemetry.socorro_crash)
===================================

Socorro exports specific crash report data to Telemetry. This data is in the
``telemetry.socorro_crash`` data set.


Querying telemetry.socorro_crash data
=====================================

Please see the `telemetry.socorro_crash documentation
<https://docs-origin.telemetry.mozilla.org/datasets/other/socorro_crash/reference.html>`_.


Adding fields to telemetry.socorro_crash
========================================

`Open up a bug <https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&component=General&op_sys=All&product=Socorro&rep_platform=All&short_desc=please%20add%20FIELDNAME%20to%20telemetry.socorro_crash>`_
to add new fields to ``telemetry.socorro_crash``.

Fields that are crash report annotations should be documented in
`<https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml>`_.

If fields come from crash report annotations and haven't been documented, then
we may ask you to document them before we can proceed.

.. Note::

   Fields can only be added--they can't be changed.

.. Note::

   When adding a new field, data cannot be backfilled.


Things to know
==============

1. The data in ``telemetry.socorro_crash`` is from the first time a crash
   report is processed. If someone reprocesses a crash report, the changes will
   not be reflected in ``telemetry.socorro_crash``.

2. We can only add new fields to ``telemetry.socorro_crash``. We can't change
   existing fields.

3. If the crash report annotation value doesn't conform to the schema, it will
   either get dropped or result in the entire crash report getting dropped.

4. Crash report data is ingested nightly. It's not ingested over the course of
   the day. The ``telemetry.socorro_crash`` data set lags behind what you see
   on Crash Stats website.
