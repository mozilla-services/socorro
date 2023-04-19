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

``featured_versions`` *Optional* (list of strings)
    Defaults to: ``[]``

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
    based on crash reports that have been submitted. This can be combined with
    other values. This will add an item with the beta number dropped for any
    beta versions.

    **Note:** Using ``"auto"`` means that the featured versions values are
    subject to the whims of the universe.

    Use ``"KEY.PATH"`` for version values that come from a JSON-encoded file at
    a url specified by KEY in ``version_json_urls``. This will add an item with
    the beta number dropped for any beta versions.

``version_json_urls``: *Optional* (dict of key to url)
    Defaults to: ``{}``

    This is a dict of KEY to URL values where the KEY is an alphanumeric value
    used to specify the JSON-encoded data specified at URL.

    For example, if you had your version data in
    https://product-details.mozilla.org/1.0/mobile_versions.json and the data in
    that file was something like this::

        {
            "alpha_version": "114.0a1",
            "beta_version": "113.0b5",
            "ios_beta_version": "",
            "ios_version": "14.1",
            "nightly_version": "114.0a1",
            "version": "112.1.0"
        }

    and you want the ``version``, ``beta_version``, and ``nightly_version``
    keys, you would have::

        "featured_versions": [
          "product_details.version",
          "product_details.beta_version",
          "product_details.nightly_version"
        ],
        "version_json_urls": {
          "product_details": "https://product-details.mozilla.org/1.0/mobile_versions.json"
        },

    And the featured versions will be: 114.0a1, 113.0b5, 113.0b (beta number
    dropped), 112.1.0.

    **Note:** that the JSON data at the specified url is cached for an hour.

``in_buildhub`` *Optional* (bool)
    Defaults to: ``false``

    Whether or not this product has release data in `Buildhub
    <https://buildhub.moz.tools/>`_.

``bug_links`` *Optional* (list of [str, str])
    Defaults to: ``[]``

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

``product_home_links``: *Optional* (list of [str, str])
    Defaults to: ``[]``

    List of (link name, link url) links to display on the product home page.

    For example::

        "product_home_links": [
          [
            "Fenix crash monitoring documentation",
            "https://github.com/mozilla-mobile/fenix/wiki/Crash-Monitoring"
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

If you have any questions, please ask in `#crashreporting matrix channel
<https://chat.mozilla.org/#/room/#crashreporting:mozilla.org>`_.
