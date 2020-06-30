===============
Product details
===============

Summary
=======

This directory contains files that have product detail information in them.
This lets us use the GitHub interface for editing, reviewing, and merging
changes.

Products can have a file in this directory. The file is in JSON format.
Here's an example:

.. code-block:: json

   {
       "featured_versions": ["69.0a1", "68.0b8", "67.0.2"]
   }

Keys:

``featured_versions``
    List of one or more versions of this product that are currently featured.

    If you want an option for "all beta versions", end the version with ``b``
    and omit the beta number. For example, ``68.0b8`` covers just ``b8``
    whereas ``68.0b`` covers all betas for ``68``.

    For Firefox and Fennec, version strings should match the ``Version``
    annotation in the crash report or the adjusted version string determined
    by the Socorro processor's BetaVersionRule.

    For all other products, version strings should match the ``Version``
    annotation in the crash report.

    This affects the listed featured versions on the product home page and the
    "Current Versions" drop down navigation menu in the Crash Stats website.

    If this is not set, Crash Stats calculates the featured versions based on
    the crash reports that have been submitted.


How to update product details files
===================================

To make a change to one of these files, edit it in the GitHub
interface and then create a pull request.

GitHub interface: https://github.com/mozilla-services/socorro/tree/main/product_details

The pull request will be reviewed and merged by a developer.

Once merged, it may take as much as an hour for the caches in production to
expire, but after that you should be able to see the changes in production.


Questions
=========

If you have any questions, please ask in
`#breakpad:mozilla.org <https://riot.im/app/#/room/#breakpad:mozilla.org>`_.
