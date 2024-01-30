Crash pings
===========

crash report vs. crash ping
---------------------------

We have two different methods of collecting crash data.

**crash report**
    The crash reporter assembles a crash report with crash annotations and
    minidumps and some other things. It prompts the user for permission to
    submit the crash report. If the user says "yes", then the crash reporter
    submits it to the crash ingestion pipeline where it's collected, processed,
    and available in `Crash Stats <https://crash-stats.mozilla.org/>`__.

    Crash report data is off by default.

    Crash report data contains protected data which includes sensitive data,
    PII, etc.

    Not all crashes result in a crash report sent to the crash ingestion
    pipeline for various technical reasons.

    Not all users say "yes" to submit the crash report.

    The crash ingestion pipeline throttles crash reports. For example, it only
    accepts 10% of incoming Firefox desktop release channel crash reports and
    rejects the rest.

    .. Seealso::

       Collector throttle rules:
           https://github.com/mozilla-services/antenna/blob/main/antenna/throttler.py


**crash ping**
    The crash reporter walks the stack and assembles a crash ping which a
    subset of crash annotation data. It sends this using Telemetry clients to
    the Telemetry data ingestion pipeline. It is available in the
    ``telemetry.crash`` BigQuery table.


    Crash ping data is on by default and shares opt-out mechanisms with
    Telemetry data submission.

    Crash ping data does not contain protected data.

    As of 2022-10-18, we only support crash ping data with Firefox.

    .. Seealso::

       Crash ping documentation:
           https://docs.telemetry.mozilla.org/datasets/pings.html#crash-ping


.. Seealso::

   Older blog post on crash reports vs. crash pings (2019):
       https://bluesock.org/~willkg/blog/mozilla/crash_pings_crash_reports.html


Updating crash ping schema
--------------------------

After someone has added a new field to `CrashAnnotations.yaml
<https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml>`__
which has ``ping: true`` in it, we do the following:

1. From a mozilla-pipeline-schemas (https://github.com/mozilla-services/mozilla-pipeline-schemas/)
   checkout, run::

      scripts/extract_crash_annotation_fields /path/to/mozilla-unified/toolkit/crashreporter/CrashAnnotations.yaml

   If any exist, you will get a list of crash annotations that are contained
   in the ping but are not yet in the schema.

2. Add the annotation to ``templates/telemetry/crash/crash.4.schema.json`` under
   the ``payload/metadata`` section.

3. Follow `<https://github.com/mozilla-services/mozilla-pipeline-schemas#cmake-build-instructions>`_ to
   build the schema files.

4. Create a pull request against the main branch in mozilla-pipeline-schemas
   referencing that bug.

   Example: https://github.com/mozilla-services/mozilla-pipeline-schemas/pull/711
