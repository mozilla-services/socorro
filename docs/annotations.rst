.. _annotations-chapter:

=================
Crash Annotations
=================

A crash report contains a set of *crash annotations* and zero or more
minidumps. For example, a crash report may contain the following annotations:

* **ProductName**: Firefox
* **Version**: 77.0a1
* **ReleaseChannel**: nightly

Annotations are documented in
`CrashAnnotations.yaml <https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml>`_.


Adding new crash annotations to a crash report
==============================================

1. First, check
   `CrashAnnotations.yaml <https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml>`_.

   Verify your annotation doesn't already exist with a different name. You can't
   change the meaning or type of an existing annotation.

2. New annotations need to undergo data collection review:
   https://wiki.mozilla.org/Firefox/Data_Collection

   Some things to keep in mind when filling out the review request:

   1. If the field will be available in crash pings sent to Telemetry, make
      sure that's mentioned in the data collection review request.

   2. Collection of crash annotation data never expires.

      The answer to:

          How long will this data be collected?

      is:

          I want to permanently monitor this data.

      And the data request must specify an owner for this data collection.

   3. Crash annotation data sent in crash reports is opt-in by default, bug
      crash pings are opt-out by default.

      If you only want the crash annotation data showing up in crash reports
      and showing up in Crash Stats, then:

          If this data collection is default on, what is the opt-out mechanism
          for users?

      is answered as:

          No mechanism is required.

      If you also want the crash annotation data showing up in crash pings, then:

          If this data collection is default on, what is the opt-out mechanism
          for users?

      is answered as:

          This data is opt-out via the normal telemetry opt-out mechanism.

3. Once a new annotation is approved, details about the annotation need to be
   added to the ``CrashAnnotations.yaml`` file.

   If the field also needs to be available in crash pings sent to Telemetry,
   you need to add ``ping: true`` to ``CrashAnnotations.yaml``

   For example::

      AsyncShutdownTimeout:
        description: >
          This annotation is present if a shutdown blocker was not released in time
          and the browser was crashed instead of waiting for shutdown to finish. The
          condition that caused the hang is contained in the annotation.
        type: string
        ping: true


3. Add the code to put the annotation in the crash report. Once a new
   annotation is added to a crash report, Socorro will save it with crash data.

4. (Optional) If you want the field to show up in crash pings sent to Telemetry,
   you have to update their schema, too.

   1. From a mozilla-pipeline-schemas (https://github.com/mozilla-services/mozilla-pipeline-schemas/)
      checkout, run::

         scripts/extract_crash_annotation_fields /path/to/mozilla-unified/toolkit/crashreporter/CrashAnnotations.yaml

      If any exist, you will get a list of crash annotations that are contained in the ping but are not yet in the schema.

   3. Copy them into ``templates/telemetry/crash/crash.4.schema.json`` under the ``payload/metadata`` section.

   4. File a bug to add them under ``Data Platform and Tools :: Datasets General``.
      Then create a pull request against mozilla-pipeline-schemas referencing that bug.

5. (Optional) `File a "support field" bug <https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&component=Generalform_name=enter_bug&op_sys=All&product=Socorro&rep_platform=All&short_desc=support%20XXX%20field>`_
   to request support for your crash annotation in Crash Stats to:

   * make it public
   * make it searchable in Super Search
   * make it aggregatable in Super Search
   * add any additional processing in Socorro for the field

6. (Optional) `File a "send field to telemetry" bug <https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&component=Generalform_name=enter_bug&op_sys=All&product=Socorro&rep_platform=All&short_desc=send%20XXX%20field%20to%20telemetry>`_
   to make it available in ``telemetry.crash_reports`` and correlations on
   Crash Stats.
