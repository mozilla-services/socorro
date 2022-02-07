===============
Product details
===============

Summary
=======

This directory contains a file for each product that Socorro supports along
with its configuration and settings. This lets us use the GitHub interface for
editing, reviewing, and merging changes.

Each product file in this directory is in JSON format. Here's an example:

.. code-block:: json

   {
     "name": "Firefox",
     "home_page_sort": 1,
     "featured_versions": ["auto"],
     "bug_links": [
       [
         "Firefox",
         "https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=%(bug_type)s&keywords=crash&product=Firefox&op_sys=%(op_sys)s&rep_platform=%(rep_platform)s&cf_crash_signature=%(signature)s&short_desc=%(title)s&comment=%(description)s&format=__default__"
       ]
     ]
   }

Keys:

``name`` (string)
    The name of the product. This dictates how it appears on the site.

``description`` (string)
    One-line description of the product.

``home_page_sort`` (int)
    Dictates the sort order of this product.

``featured_versions`` (list of strings)
    List of one or more versions of this product that are currently featured.

    If you want an option for "all beta versions", end the version with ``b``
    and omit the beta number. For example, ``68.0b8`` covers just ``b8``
    whereas ``68.0b`` covers all betas for ``68``.

    For Firefox, version strings should match the ``Version`` annotation in the
    crash report or the adjusted version string determined by the Socorro
    processor's BetaVersionRule.

    For all other products, version strings should match the ``Version``
    annotation in the crash report.

    This affects the listed featured versions on the product home page and the
    "Current Versions" drop down navigation menu in the Crash Stats website.

    Use ``"auto"`` if you want Crash Stats to calculate the featured versions
    based on crash reports that have been submitted.

``in_buildhub`` (bool)
    Whether or not this product has release data in `Buildhub
    <https://buildhub.moz.tools/>`_.

``bug_links`` (list of [str, str])
    List of "create a bug" links to show in the Bugzilla tab in the crash report.
    The first string is the text for the link. The second string is the url
    template. It's allowed to have the following keys in it:

    * bug_type: set to "defect"
    * op_sys: the operating system
    * rep_platform: the architecture
    * signature: the crash signature
    * title: bug title
    * description: the bug description in Markdown format

    For example::

       "bug_links": [
         [
           "Firefox",
           "https://bugzilla.mozilla.org/enter_bug.cgi?bug_type=%(bug_type)s&keywords=crash&product=Firefox&op_sys=%(op_sys)s&rep_platform=%(rep_platform)s&cf_crash_signature=%(signature)s&short_desc=%(title)s&comment=%(description)s&format=__default__"
         ]
       ]


How to update product details files
===================================

To make a change to one of these files, edit it in the GitHub interface and
then create a pull request.

GitHub interface: https://github.com/mozilla-services/socorro/tree/main/product_details

The pull request will be tested and validated by tests. The pull request will
be reviewed and merged by a developer.

Once changes are merged, they must be deployed to production before changes can
be seen.


Questions
=========

If you have any questions, please ask in
`#crashreporting:mozilla.org <https://riot.im/app/#/room/#crashreporting:mozilla.org>`_.
