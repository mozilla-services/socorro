.. _annotations-chapter:

=================
Crash Annotations
=================

A breakpad-style crash report contains one or more minidumps plus a series of
*crash annotations*. For example, a crash report may contain the following
annotations:

* **ProductName**: Firefox
* **Version**: 77.0a1
* **ReleaseChannel**: nightly


Annotations are documented in `CrashAnnotations.yaml <https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml>`_.


Adding new crash annotations to a crash report
==============================================

1. Check `CrashAnnotations.yaml <https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml>`_.

   Crash annotations you're adding shouldn't change the meaning of existing annotations.

   New crash annotations should get documented in that file.

   .. Note::

      If the field will be available in crash pings sent to Telemetry, make
      sure to add ``ping: true`` to CrashAnnotations.yaml.

2. New annotations need to undergo data collection review:
   https://wiki.mozilla.org/Firefox/Data_Collection

   .. Note::

      If the field will be available in crash pings sent to Telemetry, make
      sure that's mentioned in the data collection review request.

3. Once a new annotation is added to a crash report, Socorro will accept it.

4. (Optional) `File a bug <https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&component=Generalform_name=enter_bug&op_sys=All&product=Socorro&rep_platform=All&short_desc=support%20XXX%20field>`_
   to request support for your crash annotation in Crash Stats to:

   * make it public
   * make it searchable in supersearch
   * make it aggregatable in supersearch
   * add any additional processing in Socorro for the field

5. (Optional) `File a bug <https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&component=Generalform_name=enter_bug&op_sys=All&product=Socorro&rep_platform=All&short_desc=send%20XXX%20field%20to%20telemetry>`_
   to make it available in ``telemetry.crash_reports`` and correlations on
   Crash Stats
