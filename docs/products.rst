.. _products-chapter:

=======================
Products on Crash Stats
=======================

The Socorro crash ingestion pipeline handles incoming crash reports for Mozilla
products. Crash reports are collected, processed, and available for search and
analysis using the Crash Stats web site.

Socorro supports specific products. If the product isn't supported, then the
Socorro collector will reject those crash reports.

Product support is implemented in two places:

1. The collector has a list of supported products. Crash reports that have a
   ``ProductName`` that isn't in the list of supported products are rejected.

   https://github.com/mozilla-services/antenna/blob/main/antenna/throttler.py

2. Crash Stats uses the configuration in the files in the ``product_details/``
   directory to define how products show up in the Crash Stats site.

   https://github.com/mozilla-services/socorro/tree/main/product_details

For information on how to request new products be added to or products to be
removed from Mozilla's crash ingestion system, see `Crash Stats documentation
<https://crash-stats.mozilla.org/documentation/>`__.
