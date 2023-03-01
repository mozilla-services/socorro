.. _annotations-chapter:

=================
Crash Annotations
=================

A crash report contains a set of *crash annotations*. For example, a crash
report may contain the following annotations:

==================  =======
annotation name     value
==================  =======
``ProductName``     Firefox
``Version``         77.0a1
``ReleaseChannel``  nightly
==================  =======

Crash annotations for all Mozilla products are documented in
`CrashAnnotations.yaml`_.

.. _CrashAnnotations.yaml: https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml


Adding new crash annotations
============================

.. Note::

   If you need any help with this, please ask on `#crashreporting on Matrix
   <https://chat.mozilla.org/#/room/#crashreporting:mozilla.org>`__.


Follow these steps for adding new crash annotations to a crash report:

1. Check `CrashAnnotations.yaml`_.

   Verify that the annotation you want to add doesn't already exist with a
   different name and that there isn't an annotation with that name already.

   **You can't change the meaning or type of an existing annotation.**

2. Get a data collection review.

   Whenever you add a new crash annotation, it must pass a data review first.

   See :ref:`annotations-chapter-data-review`.

3. Once the data review for the new crash annotation is approved, the
   annotation needs to be documented in the `CrashAnnotations.yaml`_ file.

   Example of a crash annotation that will be in crash reports::

      AsyncShutdownTimeout:
        description: >
          This annotation is present if a shutdown blocker was not released in time
          and the browser was crashed instead of waiting for shutdown to finish. The
          condition that caused the hang is contained in the annotation.
        type: string


   If you want the crash annotation to also be available in crash pings sent to
   Telemetry, you need to add ``ping: true`` to `CrashAnnotations.yaml`_

   Example of a crash annotation that will be in crash reports AND crash pings::

      AsyncShutdownTimeout:
        description: >
          This annotation is present if a shutdown blocker was not released in time
          and the browser was crashed instead of waiting for shutdown to finish. The
          condition that caused the hang is contained in the annotation.
        type: string
        ping: true


4. Add the code to put the annotation in the crash report.

   As soon as that code is merged and new builds are created and crash reports
   start adding the crash annotation, the crash annotation data will be
   available in Crash Stats and require protected data access.


Supporting crash annotations
============================

Once the crash annotation is being sent by the crash reporter, you want to be
able to analyze it. There are several things you can do.


Support on Crash Stats (publicly viewable, searchable, etc)
-----------------------------------------------------------

Crash Stats is the site we use for accessing and analyzing crash report data
processed by the crash ingestion pipeline.

`File a "support new annotation" bug
<https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&comment=I%20would%20like%20to%20add%20support%20for%20crash%20annotation%20XYZ%20to%20Crash%20Stats.%0D%0A%0D%0AI%20would%20like%20to%20%28pick%20the%20ones%20that%20apply%29%3A%0D%0A%0D%0A%2A%20make%20this%20annotation%20public%0D%0A%2A%20make%20this%20annotation%20searchable%20in%20Super%20Search%0D%0A%2A%20make%20this%20annotation%20aggregatable%20in%20Super%20Search%0D%0A%2A%20add%20additional%20processing%20for%20this%20annotation%0D%0A%0D%0AThe%20data%20review%20for%20this%20field%20is%20in%20bug%20%23XYZ.&component=General&contenttypemethod=list&contenttypeselection=text%2Fplain&defined_groups=1&filed_via=standard_form&form_name=enter_bug&op_sys=All&product=Socorro&rep_platform=All&short_desc=support%20crash%20annotation%20XYZ>`__
to request support for your crash annotation in Crash Stats for any of the
following:

* make it public
* make it searchable in Super Search
* make it aggregatable in Super Search
* add any additional processing in Socorro for the field


Sent in the crash ping data and available in telemetry.crash
------------------------------------------------------------

The crash reporter sends crash report data to the crash ingestion pipeline. It
also sends a subset of this data in crash pings directly to Telemetry.

If you want the crash annotation data sent in the crash ping, make sure you marked
``ping: true`` in `CrashAnnotations.yaml`_.

`File a bug in Data Platform and Tools :: Datasets: General
<https://bugzilla.mozilla.org/enter_bug.cgi?comment=Please%20add%20the%20following%20crash%20annotations%20to%20the%20crash%20ping%20schema%3A%0D%0A%0D%0A%2A%20%0D%0A%0D%0AThe%20data%20review%20for%20these%20annotations%20is%20bug%20%23XYZ.&component=Datasets%3A%20General&bug_type=task&product=Data%20Platform%20and%20Tools&rep_platform=Unspecified&short_desc=add%20crash%20annotation%20XYZ%20to%20crash%20ping%20schema>`__
to request the crash ping schema be updated so that the crash annotation shows
up in the crash ping data.

Feel free to needinfo ``Will Kahn-Greene [:willkg]``.


Support in telemetry.socorro_crash
----------------------------------

Socorro processes incoming crash reports and stores them for analysis using
Crash Stats.

Socorro also sends a subset of crash report data to Telemetry. This data is
imported and stored in the ``telemetry.socorro_crash`` BigQuery table.

See :ref:`telemetry-chapter` for details on how to use this data.

`File a "send field to telemetry" bug
<https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=task&comment=I%20would%20like%20to%20have%20crash%20annotation%20XYZ%20sent%20to%20Telemetry%20and%20included%20in%20the%20%60telemetry.socorro_crash%60%20table.%0D%0A%0D%0AThe%20data%20review%20for%20this%20field%20is%20in%20bug%20%23XYZ.&component=General&contenttypemethod=list&contenttypeselection=text%2Fplain&defined_groups=1&filed_via=standard_form&form_name=enter_bug&op_sys=All&product=Socorro&rep_platform=All&short_desc=send%20crash%20annotation%20XYZ%20to%20telemetry.socorro_crash>`_,
if you want the crash annotation data available in the
``telemetry.socorro_crash`` BigQuery table.


.. _annotations-chapter-data-review:

Getting a data review for crash annotations
===========================================

This crash annotation data review template is based on `the data review request
template <https://github.com/mozilla/data-review/blob/main/request.md>`_.

Follow these steps:

1. Take this template and fill it out completely as a text file.

2. Attach the completed data review request as a text file to:

   * the bug for adding the collection code for this annotation, OR
   * a new bug in your own component for adding this annotation

3. Notify a data steward to review the request.

   Flag the attached, completed request form for ``data-review`` by setting the
   ``data-review`` flag to ``?`` and choosing a data steward.

   Data stewards are listed on the `Data Collection
   <https://wiki.mozilla.org/Data_Collection>`__ wiki page.

   Any data steward can review a data review request, but feel free to tag
   ``Will Kahn-Greene [:willkg]`` with the data review requests for crash
   annotations.

   **If the annotation is category 3 or 4, it will need to undergo Sensitive Data
   Review.**

   See `Sensitive Data Review
   <https://wiki.mozilla.org/index.php?title=Data_Collection#Step_3:_Sensitive_Data_Collection_Review_Process>`__
   for more details.

If you need any help with filing a data review request, ask on `#crashreporting
on Matrix <https://chat.mozilla.org/#/room/#crashreporting:mozilla.org>`__.

Template for data review for crash annotations:

::

    Request for data collection review form
    =======================================

    All questions are mandatory. You must receive review from a data steward
    peer on your responses to these questions before shipping new data
    collection.

    (If you want this crash annotation data to be in BOTH crash reports AND
    crash pings, include this line. Otherwise remove it.)

    This data review covers a crash annotation to be sent in both crash reports
    and crash pings.


    1) What questions will you answer with this data?


    2) Why does Mozilla need to answer these questions?  Are there benefits for
    users? Do we need this information to address product or business
    requirements?

    Some example responses:

    * Establish baselines or measure changes in product or platform quality or
      performance.

    * Provide information essential for advancing a business objective such as
      supporting OKRs.

    * Determine whether a product or platform change has an effect on user or
      browser behavior.


    3) What alternative methods did you consider to answer these questions? Why
    were they not sufficient?


    4) Can current instrumentation answer these questions?


    5) List all proposed annotations and indicate the category of data
    collection for each measurement, using the "Firefox data collection
    categories" (https://wiki.mozilla.org/Data_Collection) found on the Mozilla
    wiki. Note that the data steward reviewing your request will characterize
    your data collection based on the highest (and most sensitive) category.

    (Use this template for each proposed annotation.)

    * Annotation description:
    * Data collection category:
    * Tracking bug #:


    6) Please provide a link to the documentation for this data collection
    which describes the ultimate data set in a public, complete, and accurate
    way. Often the Privacy Notice for your product will link to where the
    documentation is expected to be.

    Documentation for crash annotations is in
    https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml


    7) How long will this data be collected?

    * I want to permanently monitor this data. (Put name of who owns this data
      here.)


    8) What populations will you measure?

    * Which release channels?

    * Which countries?

    * Which locales?

    * Any other filters?  Please describe in detail below.


    9) If this data collection is default on, what is the opt-out mechanism for
    users?

    Crash annotation data sent by crash report is opt-out by default.

    (If this data review request also covers sending the crash annotation data
    in the crash ping, include this line. Otherwise remove it.)

    Crash annotation data sent by crash ping is opt-out via the normal
    telemetry opt-out mechanism for crash ping data.


    10) Please provide a general description of how you will analyze this data.


    11) Where do you intend to share the results of your analysis?

    Crash annotation data is available on the Crash Stats website.


    12) Is there a third-party tool (i.e. not Glean or Telemetry) that you are
    proposing to use for this data collection? If so:

    * Are you using that on the Mozilla backend? Or going directly to the third-party?
