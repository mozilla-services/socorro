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


How to add crash reporting to your product
==========================================

You need to set up a crash reporting client and handler and hook it into
your code.

There's documentation on how this works in Firefox here:

https://firefox-source-docs.mozilla.org/toolkit/crashreporter/crashreporter/index.html

There's documentation on how this works for Android products like Fenix here:

https://github.com/mozilla-mobile/android-components/tree/master/components/lib/crash

Crash annotations are listed and described here:

https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml


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
`#crashreporting matrix channel <https://chat.mozilla.org/#/room/#crashreporting:mozilla.org>`_.


Guidelines for crash report annotations
=======================================

Minimum crash annotations for products are these:

* `ProductName`_
* `Version`_
* `ReleaseChannel`_
* `Vendor`_
* `ProductID`_
* `BuildID`_


ProductName
-----------

``ProductName`` specifies which product the crash report came from.

Incoming crash reports for Firefox desktop have a ``ProductName`` value of
``Firefox``. The Firefox crash reporter sets this using the value
``MOZ_APP_BASENAME`` in ``browser/confvars.sh``.

Incoming crash reports for GeckoView-based products have ``ProductName`` set to
the app name argument when setting up ``MozillaSocorroService``.  See the
`documentation for MozillaSocorroService
<https://github.com/mozilla-mobile/android-components/blob/master/components/lib/crash/README.md#sending-crash-reports-to-mozilla-socorro>`_
for details.

``ProductName`` is used when throttling crash reports in the collector,
applying product-specific rules in the processor, and searching/aggregating in
the Crash Stats webapp.


Version
-------

``Version`` specifies the version of the application that crashed. Socorro
supports two version formats:

1. Firefox versioning. Examples: 90.0, 90.0.1, 90.0a1, 90.0rc2, 90.0b2
2. Semantic versioning. Examples: 90.0.0, 90.0.0-alpha.1,

.. Note::

   Please use one of those formats. If you use something different, then Crash
   Stats will likely have difficulties calculating featured versions.

``Version`` is used to populate the version menu and determine featured
versions in the Crash Stats site.

Firefox and Thunderbird
    Firefox and Thunderbird use the Firefox versioning scheme.

    The Socorro processor fixes the version for incoming crash reports for
    Firefox beta release channel by adding a ``b`` and then a beta number like
    ``X.YbN``. For example, 90.0b1.

    The Socorro processor fixes the version for incoming crash reports for ESR
    releases by adding ``esr`` to the version.

Fenix
    Fenix version numbers use semantic versioning except the nightly channel.

    The Socorro processor changes the version of older Fenix nightly crash
    reports from ``Nightly YYMMDD HH:MM``  to ``0.0a1``.

    Current Fenix nightly crash reports use the same version as GeckView that
    the build ships with. The version for that uses the Firefox versioning
    scheme. For example ``90.0a1``.


ReleaseChannel
--------------

``ReleaseChannel`` specifies the update channel the user was using when the
product crashed.

Example release channels:

* ``release``
* ``beta``
* ``nightly``
* ``esr``

``ReleaseChannel`` is used when throttling crash reports in the collector and
searching/aggregating in the Crash Stats webapp.


Vendor
------

``Vendor`` specifies the application vendor. This should be ``mozilla`` for
builds we generated and released.


ProductID
---------

``ProductID`` is the application uuid.


BuildID
-------

``BuildID`` is the product application's build id denoting a specific build.
It's sometimes in the form of YYYYMMDDHHMMSS.

.. Note::

   The Fenix BuildID is actually the BuildID of the GeckoView component. For
   Fenix, the ApplicationBuildID is the build id for the product application.

``BuildID`` is used for throttling crash reports in the collector and linking
to build information in Buildhub in the Crash Stats webapp.


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


How to remove support for a product
===================================

There are two ways to do this:

1. Remove the ``product_details`` file AND delete all the crash report data
   in AWS S3 and Elasticsearch for that product, OR
2. Change the ``product_details`` file description to reflect that support has
   ended, wait for the data to expire, and then delete the ``product_details``
   file

If you remove the ``product_details`` file without deleting the data, then
people will get HTTP 500 errors when trying to visit crash reports that are
still in the system for the unsupported product. Links will continue to be in
signature reports and elsewhere.
