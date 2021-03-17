.. _products-chapter:

=======================
Products on Crash Stats
=======================

The Socorro crash ingestion pipeline handles incoming crash reports for Mozilla
products. Crash reports are collected, processed, and available for search and
analysis using the Crash Stats web site.

Socorro supports specific products. If the product isn't supported, then the
Socorro collector will reject those crash reports.

.. contents::


How to add a new supported product
==================================

To request a new product be added, please file
`file a bug report <https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro&component=General&short_desc=new%20product:%20YOURPRODUCT">`_.

In the bug report, please specify the following things:

1. The name of the product as you want it to show up in the Crash Stats web interface.
2. The ``ProductName`` value in the crash reports.

Make sure crash reports for your product follow our guidelines. Otherwise Crash
Stats and crash analysis may not work.

If you have any questions, please ask in
`#breakpad:mozilla.org <https://riot.im/app/#/room/#breakpad:mozilla.org>`_.


Guidelines for crash report annotations
=======================================

ProductName
-----------

Incoming crash reports have a ``ProductName`` which specifies which product the
crash report came from.

Incoming crash reports for Firefox desktop have a ``ProductName`` value of
``Firefox``. The Firefox crash reporter sets this using the value
``MOZ_APP_BASENAME`` in ``browser/confvars.sh``.

Incoming crash reports for GeckoView-based products have ``ProductName`` set to
the app name argument when setting up ``MozillaSocorroService``.  See the
`documentation for MozillaSocorroService
<https://github.com/mozilla-mobile/android-components/blob/master/components/lib/crash/README.md#sending-crash-reports-to-mozilla-socorro>`_
for details.


Version
-------

The ``Version`` annotation specifies the version of the application that crashed.
Firefox use versions in the following formats:

1. X.Y.Z -- release and beta version
2. X.Ya1 -- nightly versions

Socorro fixes the version for incoming crash reports for beta releases by
adding a ``b`` and then a beta number like ``X.Y.ZbN``.

Socorro fixes the version for incoming crash reports for ESR releases by adding
``esr`` to the version.

The version is used to populate the version menu and determine featured versions
in the Crash Stats site.


Other annotations
-----------------

For other annotations, refer to
`<https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml>`_.

For adding new annotations see :ref:`annotations-chapter`.


Collection of crash report data
===============================

Crash report data falls under category 4 of our
`data collection categories <https://wiki.mozilla.org/Firefox/Data_Collection>`_
because it contains information about the state of the application
when it crashed including memory dumps.

Collection of this data should default to off and requires user notice for
consent, share what will be sent, and allow a user to decline sending.


Product details files
=====================

Socorro supports product details files in the mozilla-services/socorro
repository.

You can use this to manually set featured versions. This is helpful if Socorro
isn't calculating them right because of bad data or extenuating circumstances.

For more details, see the `product details README
<https://github.com/mozilla-services/socorro/tree/main/product_details>`_.
