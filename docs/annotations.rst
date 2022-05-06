.. _annotations-chapter:

=================
Crash Annotations
=================

A crash report contains a set of *crash annotations* and zero or more
minidumps. For example, a crash report may contain the following annotations:

* **ProductName**: Firefox
* **Version**: 77.0a1
* **ReleaseChannel**: nightly

Annotations are documented in `CrashAnnotations.yaml`_.


.. _CrashAnnotations.yaml: https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml


Adding new crash annotations to a crash report
==============================================

1. First, check
   `CrashAnnotations.yaml`_

   Verify that the annotation you want to add doesn't already exist with a
   different name and that there isn't an annotation with that name already.

   You can't change the meaning or type of an existing annotation.

2. New annotations need to undergo data collection review:
   https://wiki.mozilla.org/Firefox/Data_Collection

   If you're creating a new annotation or adjusting an existing annotation, you
   should use:
   `<https://github.com/mozilla/data-review/blob/main/request.md>`_.

   Here are some things to keep in mind when filling out the review request:

   1. If the field will be available in crash reports AND crash pings, make
      sure that's mentioned in the data collection review request. It's
      easiest if it's noted at the top.

      ::

          This data review covers a crash annotation to be sent in both crash
          reports and crash pings.

   2. Link to the documentation can be a link to `CrashAnnotations.yaml`_.

      ::

          6. Please provide a link to the documentation for this data
             collection which describes the ultimate data set in a
             public, complete, and accurate way.

          Documentation is in
          https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml

   3. Crash annotation data is collected forever.

      ::

          7. How long will this data be collected? Choose one of the following:

          I want to permanently monitor this data. (put someone's name here)

      Make sure to specify someone.

   4. Crash annotation data sent in crash reports is *opt-in by default*, but
      crash pings are *opt-out by default*.

      If you want the annotation ONLY in crash reports, answer this way::

          9. If this data collection is default on, what is the opt-out
             mechanism for users?

          No mechanism is required for crash report data.

      If you want the annotation showing up in crash reports AND in crash pings,
      answer this way::

          9. If this data collection is default on, what is the opt-out
             mechanism for users?

          This data is opt-out via the normal telemetry opt-out mechanism for
          crash ping data.


   .. Note::

      If you need any help with this step, ask on #crashreporting on Matrix.

      Any data steward can review a data review request, but feel free to tag
      ``:willkg`` with the data review requests for crash annotations.

3. Once the data review for the new annotation is approved, details about the
   annotation need to be added to the `CrashAnnotations.yaml`_ file.

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


4. Add the code to put the annotation in the crash report.

   As soon as that code is merged and new builds are created and crash reports
   start adding the annotation, the annotation data will be available in Crash
   Stats and require protected data access.

5. (Optional) If you want the field to show up in crash pings sent to Telemetry,
   you have to update their schema, too.

   1. From a mozilla-pipeline-schemas (https://github.com/mozilla-services/mozilla-pipeline-schemas/)
      checkout, run::

         scripts/extract_crash_annotation_fields /path/to/mozilla-unified/toolkit/crashreporter/CrashAnnotations.yaml

      If any exist, you will get a list of crash annotations that are contained
      in the ping but are not yet in the schema.

   2. File a bug to add the annotation to crash pings under ``Data Platform and
      Tools :: Datasets: General``.

      Example: https://bugzilla.mozilla.org/show_bug.cgi?id=1745803

   3. Add the annotation to ``templates/telemetry/crash/crash.4.schema.json`` under
      the ``payload/metadata`` section.

   4. Follow `<https://github.com/mozilla-services/mozilla-pipeline-schemas#cmake-build-instructions>`_ to
      build the schema files.

   5. Create a pull request against the main branch in mozilla-pipeline-schemas
      referencing that bug.

      Example: https://github.com/mozilla-services/mozilla-pipeline-schemas/pull/711

   .. Note::

      If you need any help with this step, ask on #telemetry on Matrix. or
      #data-help on Slack, or needinfo :willkg in a bug.

6. (Optional) `File a "support new annotation" bug <https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&component=Generalform_name=enter_bug&op_sys=All&product=Socorro&rep_platform=All&short_desc=support%20XXX%20field>`_
   to request support for your crash annotation in Crash Stats to:

   * make it public
   * make it searchable in Super Search
   * make it aggregatable in Super Search
   * add any additional processing in Socorro for the field

   .. Note::

      If you need any help with this step, ask on #crashreporting on Matrix.

7. (Optional) `File a "send field to telemetry" bug <https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&component=Generalform_name=enter_bug&op_sys=All&product=Socorro&rep_platform=All&short_desc=send%20XXX%20field%20to%20telemetry>`_
   to make it available in ``telemetry.socorro_crash`` (BigQuery table for
   crash report data exported from Socorro) and correlations on Crash Stats.

   .. Note::

      If you need any help with this step, ask on #crashreporting on Matrix.
