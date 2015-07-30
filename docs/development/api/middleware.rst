.. index:: middleware

.. _middleware-chapter:

Middleware API
==============


If you would like to add a new middleware service,
:ref:`addaservice-chapter` provides an introduction on how to do that.

API map
-------

Documented services
^^^^^^^^^^^^^^^^^^^

* `/backfill/ <#backfill-service>`_
* `/bugs/ <#bugs-service>`_
* `/correlations/ <#correlations-service>`_
* `/correlations/signatures/ <#correlation-signatures-service>`_
* `/crash/ <#crash-service>`_
* `/crash_data/ <#crash-data-service>`_
* /crashes/
    * `/crashes/count_by_day <#crashes-count-by-day-service>`_
    * `/crashes/comments <#crashes-comments-service>`_
    * `/crashes/daily <#crashes-daily-service>`_
    * `/crashes/frequency  <#crashes-frequency-service>`_
    * `/crashes/paireduuid <#crashes-paireduuid-service>`_
    * `/crashes/signatures <#crashes-signatures-service>`_
    * `/crashes/signature_history <#crashes-signature-history-service>`_
    * `/crashes/exploitability <#crashes-exploitability-service>`_
    * `/crashes/adu_by_signature <#crashes-per-adu-by-signature-service>`_
* `/crashtrends/ <#crash-trends-service>`_
* `/crontabber_state/ <#crontabber-state-service>`_
* `/extensions/ <#extensions-service>`_
* `/field/ <#field-service>`_
* `/graphics_devices/ <#graphics-devices>`_
* `/job/ <#job-service>`_
* `/platforms/ <#platforms-service>`_
* `/priorityjobs/ <#priorityjobs-service>`_
* `/products/ <#products-service>`_
* `/products/builds/ <#products-builds-service>`_
* `/releases/featured/ <#releases-featured-service>`_
* `/report/list/ <#report-list-service>`_
* `/search/ <#search-service>`_
* `/server_status/ <#server-status-service>`_
* /signaturesummary/
    * `/signaturesummary/report_type/architecture/ <#architecture-signature-summary-service>`_
    * `/signaturesummary/report_type/exploitability/ <#exploitability-signature-summary-service>`_
    * `/signaturesummary/report_type/flash_version/ <#flash-version-signature-summary-service>`_
    * `/signaturesummary/report_type/distinct_install/ <#distinct-install-signature-summary-service>`_
    * `/signaturesummary/report_type/os/ <#operating-system-signature-summary-service>`_
    * `/signaturesummary/report_type/process_type/ <#process-type-signature-summary-service>`_
    * `/signaturesummary/report_type/products/ <#products-signature-summary-service>`_
    * `/signaturesummary/report_type/uptime/ <#uptime-signature-summary-service>`_
* `/signatureurls <#signature-urls-service>`_
* `/skiplist/ <#skiplist-service>`_
* `/supersearch/fields/ <#supersearch-fields-service>`_
* `/suspicious/ <#suspicious-crash-signatures-service>`_


.. ############################################################################
   Backfill API
   ############################################################################

Backfill service
----------------

Trigger a specific backfill.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                  |
+----------------+--------------------------------------------------------------------------------------+
| URL            | /backfill/(parameters)                                                               |
+----------------+--------------------------------------------------------------------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

When ``backfill_type`` equals to ``adu``, ``build_adu``, ``correlations``,
``crashes_by_user_build``, ``daily_crashes``, ``exploitability``,
``explosiveness``, ``hang_report``, ``home_page_graph_build``,
``home_page_graph``, ``nightly_builds``, ``one_day``, ``signature_summary``,
``tcbs_build`` or ``tcbs``:

+------------------+------------------+-------------------+--------------------------------------------+
| Name             | Type of value    | Default value     | Description                                |
+==================+==================+===================+============================================+
| backfill_type    | String           | None              | Define which backfill to trigger           |
+------------------+------------------+-------------------+--------------------------------------------+
| update_day       | Date             | None              | Date for which backfill should run         |
+------------------+------------------+-------------------+--------------------------------------------+


When ``backfill_type`` equals to ``all_dups``, ``reports_duplicates`` or
``signature_counts``:

+------------------+------------------+-------------------+--------------------------------------------+
| Name             | Type of value    | Default value     | Description                                |
+==================+==================+===================+============================================+
| backfill_type    | String           | None              | Define which backfill to trigger           |
+------------------+------------------+-------------------+--------------------------------------------+
| start_date       | Date             | None              | Start date for which backfill should run   |
+------------------+------------------+-------------------+--------------------------------------------+
| end_date         | Date             | None              | End date for which backfill should run     |
+------------------+------------------+-------------------+--------------------------------------------+

When ``backfill_type`` equals to ``reports_clean`` or ``matviews``:

+------------------+------------------+-------------------+--------------------------------------------+
| Name             | Type of value    | Default value     | Description                                |
+==================+==================+===================+============================================+
| backfill_type    | String           | None              | Define which backfill to trigger           |
+------------------+------------------+-------------------+--------------------------------------------+
| start_date       | Date             | None              | Start date for which backfill should run   |
+------------------+------------------+-------------------+--------------------------------------------+

When ``backfill_type`` equals to ``weekly_report_partitions``:

+------------------+------------------+-------------------+---------------------------------------------------+
| Name             | Type of value    | Default value     | Description                                       |
+==================+==================+===================+===================================================+
| backfill_type    | String           | None              | Define which backfill to trigger                  |
+------------------+------------------+-------------------+---------------------------------------------------+
| start_date       | Date             | None              | Start date for which backfill should run          |
+------------------+------------------+-------------------+---------------------------------------------------+
| end_date         | Date             | None              | End date for which backfill should run            |
+------------------+------------------+-------------------+---------------------------------------------------+
| table_name       | String           | None              | Control the backfill data based on the table name |
+------------------+------------------+-------------------+---------------------------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

When ``backfill_type`` equals to ``crashes_by_user_build``, ``crashes_by_user``,
``home_page_graph_build``, ``home_page_graph``, ``tcbs_build`` or ``tcbs``:

+------------------+------------------+-------------------+--------------------------------------------+
| Name             | Type of value    | Default value     | Description                                |
+==================+==================+===================+============================================+
| check_period     | String           | '01:00:00'        | Interval to run backfill                   |
+------------------+------------------+-------------------+--------------------------------------------+

When ``backfill_type`` equals to ``rank_compare``:

+------------------+------------------+-------------------+--------------------------------------------+
| Name             | Type of value    | Default value     | Description                                |
+==================+==================+===================+============================================+
| update_day       | Date             | NULL              | Date for which backfill should run         |
+------------------+------------------+-------------------+--------------------------------------------+

When ``backfill_type`` equals to ``reports_clean``:

+------------------+------------------+-------------------+--------------------------------------------+
| Name             | Type of value    | Default value     | Description                                |
+==================+==================+===================+============================================+
| end_date         | Date             | NULL              | End date for which backfill should run     |
+------------------+------------------+-------------------+--------------------------------------------+

When ``backfill_type`` equals to ``matviews``:

+------------------+------------------+-------------------+--------------------------------------------+
| Name             | Type of value    | Default value     | Description                                |
+==================+==================+===================+============================================+
| end_date         | Date             | NULL              | End date for which backfill should run     |
+------------------+------------------+-------------------+--------------------------------------------+
| reports_clean    | Bool             | True              | Optionally disable reports_clean backfill  |
+------------------+------------------+-------------------+--------------------------------------------+
| check_period     | String           | '01:00:00'        | Interval to run backfill                   |
+------------------+------------------+-------------------+--------------------------------------------+

Return value
^^^^^^^^^^^^

On success, returns a 200 status.


.. ############################################################################
   Bugs API
   ############################################################################

Bugs service
------------

Return a list of signature - bug id associations.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------------------------------------+
| HTTP method    | POST                                                                              |
+----------------+-----------------------------------------------------------------------------------+
| URL            | /bugs/                                                                            |
+----------------+-----------------------------------------------------------------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

Only one of signatures or bugs:

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signatures     | List of strings  | None          | Signatures of bugs      |
+----------------+------------------+---------------+-------------------------+
| bugs           | List of strings  | None          | Bugs of signatures      |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None.

Return value
^^^^^^^^^^^^

In normal cases, return something like this::

    {
        "hits": [
            {
                "id": "789012",
                "signature": "mysignature"
            },
            {
                "id": "405060",
                "signature": "anothersig"
            }
        ],
        "total": 2
    }


.. ############################################################################
   Correlations API
   ############################################################################

Correlations service
--------------------

Return correlations about specific

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------+
| HTTP method    | GET             |
+----------------+-----------------+
| URL            | /correlations/  |
+----------------+-----------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+----------------------+
| Name           | Type of value    | Default value     | Description          |
+================+==================+===================+======================+
| report\_type   | String           | None              | Eg. ``core-counts``  |
+----------------+------------------+-------------------+----------------------+
| product        | String           | None              | Eg. ``Firefox``      |
+----------------+------------------+-------------------+----------------------+
| version        | String           | None              | Eg. ``24.0a1``       |
+----------------+------------------+-------------------+----------------------+
| platform       | String           | None              | Eg. ``Mac OS X``     |
+----------------+------------------+-------------------+----------------------+
| signature      | String           | None              | Full signature       |
+----------------+------------------+-------------------+----------------------+


Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Returns a structure with three keys: ``count``, ``reason`` and
``load``.::

    {
        "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
    "count": 13,
    "load": "36% (4/11) vs.  26% (47/180) amd64 with 2 cores\n18% (2/11) vs.  31% (55/180) amd64 with 4 cores"
    }

If nothing is matched for your search you still get the same three
keys but empty like this::

    {
        "reason": null,
    "count": null,
    "load": ""
    }

NOTE: The implementation currently depends on finding a ``.txt`` file
on a remote server to pull down the data. If this file (filename is
based on the parameters you pass) is not found, the response is just::

   null


.. ############################################################################
   Correlation Signatures API
   ############################################################################

Correlation Signatures service
------------------------------

Return all signatures that have correlations about specific search
parameters

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------------------+
| HTTP method    | GET                       |
+----------------+---------------------------+
| URL            | /correlations/signatures/ |
+----------------+---------------------------+


Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+--------------------------------+
| Name           | Type of value    | Default value     | Description                    |
+================+==================+===================+================================+
| report\_type   | String           | None              | Eg. ``core-counts``            |
+----------------+------------------+-------------------+--------------------------------+
| product        | String           | None              | Eg. ``Firefox``                |
+----------------+------------------+-------------------+--------------------------------+
| version        | String           | None              | Eg. ``24.0a1``                 |
+----------------+------------------+-------------------+--------------------------------+
| platforms      | List of strings  | None              | Eg. ``Mac%20OS%20X+Linux``     |
+----------------+------------------+-------------------+--------------------------------+


Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Returns a structure with the keys ``hits`` and ``total``::

    {
        "hits": [
            "js::GCMarker::processMarkStackTop(js::SliceBudget&)",
            "gfxSVGGlyphs::~gfxSVGGlyphs()",
            "mozilla::layers::ImageContainer::GetCurrentSize()"
        ],
        "total": 3
    }


.. ############################################################################
   Crash API
   ############################################################################

Crash service
-------------

Return a single crash report from its UUID.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------------------------------------+
| HTTP method    | POST                                                                              |
+----------------+-----------------------------------------------------------------------------------+
| URL            | /crash/(optional_parameters)                                                      |
+----------------+-----------------------------------------------------------------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| uuid           | String           | None          | Identifier of the crash |
|                |                  |               | report to get.          |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None.

Return value
^^^^^^^^^^^^

In normal cases, return something like this::

    {
        "hits": [
            {
                "signature": "SomeCrashSignature",
                "email": "someone@example.com",
                "url": "http://example.com/somepage",
                "addons_checked": "some addons",
                "exploitability": "high",
                "duplicate_of": 123456
            }
        ],
        "total": 1
    }


.. ############################################################################
   Crash Data API
   ############################################################################

Crash Data service
------------------

Return JSON or binary data of a crash report, given its uuid.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------+
| HTTP method    | GET          |
+----------------+--------------+
| URL            | /crash_data/ |
+----------------+--------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| datatype       | String           | None          | Type of data to get, can|
|                |                  |               | be 'raw', 'meta' or     |
|                |                  |               | 'processed'.            |
+----------------+------------------+---------------+-------------------------+
| uuid           | String           | None          | Identifier of the crash |
|                |                  |               | report to get.          |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None.

Return value
^^^^^^^^^^^^

If datatype is 'raw', returns the binary raw dump of the crash report.
If datatype is 'meta', returns the raw JSON of the crash report.
If datatype is 'processed', return the processed JSON of the crash report.


.. ############################################################################
   Crashes Count By Day API
   ############################################################################

Crashes Count By Day service
----------------------------

Returns the count of a particular signature (all aggregated) by date range.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+------------------------+
| HTTP method    | GET                    |
+----------------+------------------------+
| URL            | /crashes/count_by_day/ |
+----------------+------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+------------+---------------+---------------------------------------------------------+
| Name       | Type of value | Description                                             |
+============+===============+=========================================================+
| signature  | String        | The signature of the crash for the count.               |
+------------+---------------+---------------------------------------------------------+
| from_date  | Date          | Starting date in the format of YYYY-MM-DD               |
+------------+---------------+---------------------------------------------------------+
| to_date    | Date          | Ending date in the format of YYYY-MM-DD, does not       |
|            |               | include this day                                        |
+------------+---------------+---------------------------------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Returns in a json like this::

    {
        "hits": {
            "YYYY-MM-DD": count
        }
        "total": the number of days returned
    }


.. ############################################################################
   Crashes Comments API
   ############################################################################

Crashes Comments service
------------------------

Return a list of comments on crash reports, filtered by signatures and other
fields.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------+
| HTTP method    | GET                |
+----------------+--------------------+
| URL            | /crashes/comments/ |
+----------------+--------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                   | Type of value                 | Default value  | Description                                                                                                                                             |
+========================+===============================+================+=========================================================================================================================================================+
| products               | String or list of strings     | '`Firefox`'    | The product we are interested in. (e.g. Firefox, Fennec, Thunderbird… )                                                                                 |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| from                   | Date                          | Now - 7 days   | Search for crashes that happened after this date. Can use the following formats: '`yyyy-MM-dd`', '`yyyy-MM-dd HH:ii:ss`' or '`yyyy-MM-dd HH:ii:ss.S`'.  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| to                     | Date                          | Now            | Search for crashes that happened before this date. Can use the following formats: '`yyyy-MM-dd`', '`yyyy-MM-dd HH:ii:ss`' or '`yyyy-MM-dd HH:ii:ss.S`'. |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| versions               | String or list of strings     | None           | Restring to a specific version of the product. Several versions can be specified, separated by a + symbol.                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| os                     | String or list of strings     | None           | Restrict to an Operating System. (e.g. Windows, Mac, Linux… ) Several versions can be specified, separated by a + symbol.                               |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| reasons                | String or list of strings     | None           | Restricts search to crashes caused by this reason.                                                                                                      |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| release_channels       | String or list of strings     | None           | Restricts search to crashes with these release channels.                                                                                                |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_ids             | Integer or list of integers   | None           | Restricts search to crashes that happened on a product with this build ID.                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_from            | Integer or list of integers   | None           | Restricts search to crashes with a build id greater than this.                                                                                          |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_to              | Integer or list of integers   | None           | Restricts search to crashes with a build id lower than this.                                                                                            |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_process        | String                        | '`any`'        | Can be '`any`', '`browser`' or '`plugin`'.                                                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_type           | String                        | '`any`'        | Can be '`any`', '`crash`' or '`hang`'.                                                                                                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_in             | String or list of strings     | '`name`'       | Search for a plugin in this field. '`report\_process`' has to be set to '`plugin`'.                                                                     |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_search\_mode   | String                        | '`default`'    | How to search for this plugin. report\_process has to be set to plugin. Can be either '`default`', '`is\_exactly`', '`contains`' or '`starts\_with`'.   |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_terms          | String or list of strings     | None           | Terms to search for. Several terms can be specified, separated by a + symbol. report\_process has to be set to plugin.                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+

Return value
^^^^^^^^^^^^

In normal cases, return something like this::

    {
        "hits": [
            {
                "date_processed": "2011-03-16 06:54:56.385843",
                "uuid": "06a0c9b5-0381-42ce-855a-ccaaa2120116",
                "user_comments": "My firefox is crashing in an awesome way",
                "email": "someone@something.org"
            },
            {
                "date_processed": "2011-03-16 06:54:56.385843",
                "uuid": "06a0c9b5-0381-42ce-855a-ccaaa2120116",
                "user_comments": "I <3 Firefox crashes!",
                "email": "someone@something.org"
            }
        ],
        "total": 2
    }

If no signature is passed as a parameter, return null.


.. ############################################################################
   Crashes Daily API
   ############################################################################

Crashes Daily service
---------------------

Return crashes by active daily users.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------+
| HTTP method    | GET             |
+----------------+-----------------+
| URL            | /crashes/daily/ |
+----------------+-----------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+------------+---------------+------------------------------------------------+
| Name       | Type of value | Description                                    |
+============+===============+================================================+
| product    | String        | Product for which to get daily crashes.        |
+------------+---------------+------------------------------------------------+
| versions   | Strings       | Versions of the product for which to get daily |
|            |               | crashes.                                       |
+------------+---------------+------------------------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+-----------------+---------------+---------------+--------------------------------+
| Name            | Type of value | Default value | Description                    |
+=================+===============+===============+================================+
| from_date       | Date          | A week ago    | Date after which to get        |
|                 |               |               | daily crashes.                 |
+-----------------+---------------+---------------+--------------------------------+
| to_date         | Date          | Now           | Date before which to get       |
|                 |               |               | daily crashes.                 |
+-----------------+---------------+---------------+--------------------------------+
| os              | Strings       | None          | Only return crashes with those |
|                 |               |               | os.                            |
+-----------------+---------------+---------------+--------------------------------+
| report_type     | Strings       | None          | Only return crashes with those |
|                 |               |               | report types.                  |
+-----------------+---------------+---------------+--------------------------------+
| separated_by    | String        | None          | Separate results by 'os' as    |
|                 |               |               | well as by product and version.|
+-----------------+---------------+---------------+--------------------------------+
| date_range_type | String        | report        | Range crashes by report_date   |
|                 |               |               | ('report') or by               |
|                 |               |               | build_date ('build').          |
+-----------------+---------------+---------------+--------------------------------+

Return value
^^^^^^^^^^^^

If os, report_type and separated_by parameters are set to their default values,
return an object like the following::

    {
        "hits": {
            "Firefox:10.0": {
                "2012-12-31": {
                    "product": "Firefox",
                    "adu": 64076,
                    "crash_hadu": 4.296,
                    "version": "10.0",
                    "report_count": 2753,
                    "date": "2012-12-31"
                },
                "2012-12-30": {
                    "product": "Firefox",
                    "adu": 64076,
                    "crash_hadu": 4.296,
                    "version": "10.0",
                    "report_count": 2753,
                    "date": "2012-12-30"
                }
            },
            "Firefox:16.0a1": {
                "..."
            }
        }
    }

Otherwise, return a more complex result that can eventually be separated by
different keys. For example, if separated_by is set to "os", it will return::

    {
        "hits": {
            "Firefox:10.0:win": {
                "2012-12-31": {
                    "product": "Firefox",
                    "adu": 64076,
                    "crash_hadu": 4.296,
                    "version": "10.0",
                    "report_count": 2753,
                    "date": "2012-12-31",
                    "os": "Windows",
                    "throttle": 0.1
                }
            },
            "Firefox:10.0:lin": {
                "2012-12-31": {
                    "product": "Firefox",
                    "adu": 64076,
                    "crash_hadu": 4.296,
                    "version": "10.0",
                    "report_count": 2753,
                    "date": "2012-12-31",
                    "os": "Linux",
                    "throttle": 0.1
                }
            }
        }
    }

Note that the returned fields will differ depending on the parameters. The "os"
field will be returned when either the "os" parameter has a value or the
"separated_by" parameter is "os", and the "report_type" field will be returned
when either the "report_type" parameter has a value or the "separated_by"
parameter is "report_type".


.. ############################################################################
   Crashes Frequency API
   ############################################################################

Crashes Frequency service
-------------------------

Return the number and frequency of crashes on each OS.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------------+
| HTTP method    | GET                 |
+----------------+---------------------+
| URL            | /crashes/frequency/ |
+----------------+---------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                   | Type of value                 | Default value  | Description                                                                                                                                             |
+========================+===============================+================+=========================================================================================================================================================+
| products               | String or list of strings     | '`Firefox`'    | The product we are interested in. (e.g. Firefox, Fennec, Thunderbird… )                                                                                 |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| from                   | Date                          | Now - 7 days   | Search for crashes that happened after this date. Can use the following formats: '`yyyy-MM-dd`', '`yyyy-MM-dd HH:ii:ss`' or '`yyyy-MM-dd HH:ii:ss.S`'.  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| to                     | Date                          | Now            | Search for crashes that happened before this date. Can use the following formats: '`yyyy-MM-dd`', '`yyyy-MM-dd HH:ii:ss`' or '`yyyy-MM-dd HH:ii:ss.S`'. |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| versions               | String or list of strings     | None           | Restring to a specific version of the product. Several versions can be specified, separated by a + symbol.                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| os                     | String or list of strings     | None           | Restrict to an Operating System. (e.g. Windows, Mac, Linux… ) Several versions can be specified, separated by a + symbol.                               |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| reasons                | String or list of strings     | None           | Restricts search to crashes caused by this reason.                                                                                                      |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| release_channels       | String or list of strings     | None           | Restricts search to crashes with these release channels.                                                                                                |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_ids             | Integer or list of integers   | None           | Restricts search to crashes that happened on a product with this build ID.                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_from            | Integer or list of integers   | None           | Restricts search to crashes with a build id greater than this.                                                                                          |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_to              | Integer or list of integers   | None           | Restricts search to crashes with a build id lower than this.                                                                                            |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_process        | String                        | '`any`'        | Can be '`any`', '`browser`' or '`plugin`'.                                                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_type           | String                        | '`any`'        | Can be '`any`', '`crash`' or '`hang`'.                                                                                                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_in             | String or list of strings     | '`name`'       | Search for a plugin in this field. '`report\_process`' has to be set to '`plugin`'.                                                                     |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_search\_mode   | String                        | '`default`'    | How to search for this plugin. report\_process has to be set to plugin. Can be either '`default`', '`is\_exactly`', '`contains`' or '`starts\_with`'.   |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_terms          | String or list of strings     | None           | Terms to search for. Several terms can be specified, separated by a + symbol. report\_process has to be set to plugin.                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+

Return value
^^^^^^^^^^^^

In normal cases, return something like this::

    {
        "hits": [
            {
                "count": 167,
                "build_date": "20120129064235",
                "count_mac": 0,
                "frequency_windows": 1,
                "count_windows": 167,
                "frequency": 1,
                "count_linux": 0,
                "total": 167,
                "frequency_linux": 0,
                "frequency_mac": 0
            },
            {
                "count": 1,
                "build_date": "20120129063944",
                "count_mac": 1,
                "frequency_windows": 0,
                "count_windows": 0,
                "frequency": 1,
                "count_linux": 0,
                "total": 1,
                "frequency_linux": 0,
                "frequency_mac": 1
            }
        ],
        "total": 2
    }


.. ############################################################################
   Crashes Paireduuid API
   ############################################################################

Crashes Paireduuid service
--------------------------

Return paired uuid given a uuid and an optional hangid.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+----------------------+
| HTTP method    | GET                  |
+----------------+----------------------+
| URL            | /crashes/paireduuid/ |
+----------------+----------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+------------+---------------+------------------------------------------------+
| Name       | Type of value | Description                                    |
+============+===============+================================================+
| uuid       | String        | Unique identifier of the crash report.         |
+------------+---------------+------------------------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+------------+---------------+---------------+--------------------------------+
| Name       | Type of value | Default value | Description                    |
+============+===============+===============+================================+
| hangid     | String        | None          | Hang ID of the crash report.   |
+------------+---------------+---------------+--------------------------------+

Return value
^^^^^^^^^^^^

Return an object like the following::

    {
        "hits": [
            {
                "uuid": "e8820616-1462-49b6-9784-e99a32120201"
            }
        ],
        "total": 1
    }

Note that if a hangid is passed to the service, it will always return maximum
one result. Remove that hangid to get all paired uuid.


.. ############################################################################
   Crashes Signatures API
   ############################################################################

Crashes Signatures service
--------------------------

Return top crashers by signatures.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+----------------------+
| HTTP method    | GET                  |
+----------------+----------------------+
| URL            | /crashes/signatures/ |
+----------------+----------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+------------+---------------+------------------------------------------------+
| Name       | Type of value | Description                                    |
+============+===============+================================================+
| product    | String        | Product for which to get top crashes by        |
|            |               | signatures.                                    |
+------------+---------------+------------------------------------------------+
| version    | String        | Version of the product for which to get top    |
|            |               | crashes.                                       |
+------------+---------------+------------------------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+-----------------+---------------+---------------+--------------------------------+
| Name            | Type of value | Default value | Description                    |
+=================+===============+===============+================================+
| crash_type      | String        | all           | Type of crashes to get, can be |
|                 |               |               | "browser", "plugin", "content" |
|                 |               |               | or "all".                      |
+-----------------+---------------+---------------+--------------------------------+
| end_date        | Date          | Now           | Date before which to get       |
|                 |               |               | top crashes.                   |
+-----------------+---------------+---------------+--------------------------------+
| duration        | Int           | One week      | Number of hours during which   |
|                 |               |               | to get crashes.                |
+-----------------+---------------+---------------+--------------------------------+
| os              | String        | None          | Limit crashes to only one OS.  |
+-----------------+---------------+---------------+--------------------------------+
| limit           | Int           | 100           | Number of results to retrieve. |
+-----------------+---------------+---------------+--------------------------------+
| date_range_type | String        | 'report'      | Range by report date or        |
|                 |               |               | build date.                    |
+-----------------+---------------+---------------+--------------------------------+

Return value
^^^^^^^^^^^^

Return an object like the following::

    {
        "totalPercentage": 1.0,
        "end_date": "2012-06-28",
        "start_date": "2012-06-21",
        "crashes": [
            {
                "count": 3,
                "mac_count": 0,
                "content_count": 0,
                "first_report": "2012-03-13",
                "previousRank": 12,
                "currentRank": 0,
                "startup_percent": 0,
                "versions": "13.0a1, 14.0a1, 15.0a1, 16.0a1",
                "first_report_exact": "2012-03-13 17:58:30",
                "percentOfTotal": 0.214285714285714,
                "changeInRank": 12,
                "win_count": 3,
                "changeInPercentOfTotal": 0.20698716413283896,
                "linux_count": 0,
                "hang_count": 3,
                "signature": "hang | WaitForSingleObjectEx",
                "versions_count": 4,
                "previousPercentOfTotal": 0.00729855015287504,
                "plugin_count": 0
            },
            {
                "count": 2,
                "mac_count": 0,
                "content_count": 0,
                "first_report": "2012-06-27",
                "previousRank": "null",
                "currentRank": 1,
                "startup_percent": 0,
                "versions": "16.0a1",
                "first_report_exact": "2012-06-27 22:59:13",
                "percentOfTotal": 0.142857142857143,
                "changeInRank": "new",
                "win_count": 2,
                "changeInPercentOfTotal": "new",
                "linux_count": 0,
                "hang_count": 2,
                "signature": "hang | npswf64_11_3_300_262.dll@0x6c1d56",
                "versions_count": 1,
                "previousPercentOfTotal": "null",
                "plugin_count": 2
            }
        ],
        "totalNumberOfCrashes": 2
    }


.. ############################################################################
   Crashes Signature History API
   ############################################################################

Crashes Signature History service
---------------------------------

Return the history of a signature.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------+
| HTTP method    | GET                         |
+----------------+-----------------------------+
| URL            | /crashes/signature_history/ |
+----------------+-----------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+------------+---------------+------------------------------------------------+
| Name       | Type of value | Description                                    |
+============+===============+================================================+
| product    | String        | Name of the product.                           |
+------------+---------------+------------------------------------------------+
| version    | String        | Number of the version.                         |
+------------+---------------+------------------------------------------------+
| signature  | String        | Signature to get, exact match.                 |
+------------+---------------+------------------------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+-----------------+---------------+---------------+--------------------------------+
| Name            | Type of value | Default value | Description                    |
+=================+===============+===============+================================+
| start_date      | Datetime      | Last week     | The earliest date of crashes   |
|                 |               |               | we wish to evaluate            |
+-----------------+---------------+---------------+--------------------------------+
| end_date        | Datetime      | Now           | The latest date of crashes we  |
|                 |               |               | wish to evaluate.              |
+-----------------+---------------+---------------+--------------------------------+

Return value
^^^^^^^^^^^^

Return an object like the following::

    {
        "hits": [
            {
                "date": "2012-03-13",
                "count": 3,
                "percent_of_total": 42
            },
            {
                "date": "2012-03-20",
                "count": 6,
                "percent_of_total": 76
            }
        ],
        "total": 2
    }


.. ############################################################################
   Crashes Exploitability API
   ############################################################################

Crashes Exploitability service
------------------------------

Return a list of exploitable crash reports.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------+
| HTTP method    | GET                      |
+----------------+--------------------------+
| URL            | /crashes/exploitability/ |
+----------------+--------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

None

Optional parameters
^^^^^^^^^^^^^^^^^^^

+-----------------+---------------+---------------+----------------------------------+
| Name            | Type of value | Default value | Description                      |
+=================+===============+===============+==================================+
| start_date      | Date          | 1 week ago    | Start date of query range        |
+-----------------+---------------+---------------+----------------------------------+
| end_date        | Date          | Today         | End date of query range          |
+-----------------+---------------+---------------+----------------------------------+
| product         | String        | None          | The product we are interested in |
+-----------------+---------------+---------------+----------------------------------+
| version         | String        | None          | The version we are interested in |
+-----------------+---------------+---------------+----------------------------------+
| batch           | Int           | None          | Number of signatures to return   |
|                 |               |               | per page.                        |
+-----------------+---------------+---------------+----------------------------------+
| page            | Int           | 0             | Multiple of batch size for       |
|                 |               |               | paginating query.                |
+-----------------+---------------+---------------+----------------------------------+

Return value
^^^^^^^^^^^^

Return an object like the following::

    {
      "hits": [
        {
          "low_count": 2,
          "high_count": 1,
          "null_count": 0,
          "none_count": 0,
          "report_date": "2013-06-29",
          "signature": "lockBtree",
          "medium_count": 5,
          "product_name": "Firefox",
          "version_string": "29.0"
        },
        {
          "low_count": 0,
          "high_count": 0,
          "null_count": 0,
          "none_count": 1,
          "report_date": "2013-06-29",
          "signature": "nvwgf2um.dll@0x15cfb0",
          "medium_count": 0,
          "product_name": "Firefox",
          "version_string": "28.0"
        },
      ],
      "total": 2
    }

Crashes per ADU By Signature service
------------------------------

Return a list of crash and ADU counts by signature.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+------------------------------------+
| HTTP method    | GET                                |
+----------------+------------------------------------+
| URL            | /crashes/adu_by_signature/         |
+----------------+------------------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+-----------------+---------------+---------------+------------------------------------+
| Name            | Type of value | Default value | Description                        |
+=================+===============+===============+====================================+
| product_name    | String        | None          | The product we are interested in   |
+-----------------+---------------+---------------+------------------------------------+
| start_date      | Date          | 1 week ago    | Start date of query range          |
+-----------------+---------------+---------------+------------------------------------+
| end_date        | Date          | Today         | End date of query range            |
+-----------------+---------------+---------------+------------------------------------+
| signature       | String        | None          | The signature we are interested in |
+-----------------+---------------+---------------+------------------------------------+
| channel         | String        | None          | The channel we are interested in   |
+-----------------+---------------+---------------+------------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Return an object like the following::

    {
        "hits": [
            {
                "signature": "gfxContext::PushClipsToDT(mozilla::gfx::DrawTarget*)",
                "adu_date": "2014-03-01",
                "build_date": "2014-03-01",
                "buildid": '201403010101',
                "crash_count": 3,
                "adu_count": 1023,
                "os_name": "Mac OS X",
                "channel": "release"
            },
            {
                "signature": "gfxContext::PushClipsToDT(mozilla::gfx::DrawTarget*)"
                "adu_date": "2014-04-01",
                "build_date": "2014-04-01",
                "buildid": '201404010101',
                "crash_count": 4,
                "adu_count": 1024,
                "os_name": "Windows NT",
                "channel": "release"
            },
        ],
        "total": 2,
    }


.. ############################################################################
   Crash Trends API
   ############################################################################

Crash Trends service
--------------------

Return a list of nightly or aurora crashes that took place between two dates.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------+
| HTTP method    | GET           |
+----------------+---------------+
| URL            | /crashtrends/ |
+----------------+---------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+---------------+---------------+---------------+-----------------------------------+
| Name          | Type of value | Default value | Description                       |
+===============+===============+===============+===================================+
| start_date    | Datetime      | None          | The earliest date of crashes      |
|               |               |               | we wish to evaluate               |
+---------------+---------------+---------------+-----------------------------------+
| end_date      | Datetime      | None          | The latest date of crashes we     |
|               |               |               | wish to evaluate.                 |
+---------------+---------------+---------------+-----------------------------------+
| product       | String        | None          | The product.                      |
+---------------+---------------+---------------+-----------------------------------+
| version       | String        | None          | The version.                      |
+---------------+---------------+---------------+-----------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Return a total of crashes, along with their build date, by build ID::

    [
        {
            "build_date": "2012-02-10",
            "version_string": "12.0a2",
            "product_version_id": 856,
            "days_out": 6,
            "report_count": 515,
            "report_date": "2012-02-16",
            "product_name": "Firefox"
        }
    ]


.. ############################################################################
   Crontabber State API
   ############################################################################

Crontabber State service
------------------------

Return the current state of crontabber.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------+
| HTTP method    | GET                |
+----------------+--------------------+
| URL            | /crontabber_state/ |
+----------------+--------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

None

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Returns a structure with two main keys ``state`` and ``last_updated``.
In ``state`` we get the parsed state from the ``crontabber_state``
table.::

    {
        "state": {
          "slow-one": {
            "next_run": "2013-02-09 01:16:00.893834",
            "first_run": "2012-11-05 23:27:07.316347",
            "last_error": {
              "traceback": "error error error",
              "type": "<class 'sluggish.jobs.InternalError'>",
              "value": "Have already run this for 2012-12-24 23:27"
            },
            "last_run": "2013-02-09 00:16:00.893834",
            "last_success": "2012-12-24 22:27:07.316893",
            "error_count": 6,
            "depends_on": []
          },
          "slow-two": {
            "next_run": "2012-11-12 19:39:59.521605",
            "first_run": "2012-11-05 23:27:17.341879",
            "last_error": {},
            "last_run": "2012-11-12 18:39:59.521605",
            "last_success": "2012-11-12 18:27:17.341895",
            "error_count": 0,
            "depends_on": ["slow-one"]
          }
        },
        "last_updated": "2000-01-01T00:00:00+00:00"
    }


.. ############################################################################
   Extensions API
   ############################################################################

Extensions service
------------------

Return a list of extensions associated with a crash's UUID.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------+
| HTTP method    | GET          |
+----------------+--------------+
| URL            | /extensions/ |
+----------------+--------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+---------+---------------+---------------+-----------------------------------+
| Name    | Type of value | Default value | Description                       |
+=========+===============+===============+===================================+
| uuid    | String        | None          | Unique Identifier of the specific |
|         |               |               | crash to get extensions from.     |
+---------+---------------+---------------+-----------------------------------+
| date    | Datetime      | None          | Exact datetime of the crash.      |
+---------+---------------+---------------+-----------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Return a list of extensions::

    {
        "total": 1,
        "hits": [
            {
                "report_id": 1234,
                "date_processed": "2012-02-29T01:23:45+00:00",
                "extension_key": 5678,
                "extension_id": "testpilot@labs.mozilla.com",
                "extension_version": "1.2"
            }
        ]
    }


.. ############################################################################
   Field API
   ############################################################################

Field service
-------------

Return data about a field from its name.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------+
| HTTP method    | GET     |
+----------------+---------+
| URL            | /field/ |
+----------------+---------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+---------+---------------+---------------+-----------------------------------+
| Name    | Type of value | Default value | Description                       |
+=========+===============+===============+===================================+
| name    | String        | None          | Name of the field.                |
+---------+---------------+---------------+-----------------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Return a dictionary::

    {
        "name": "my-field",
        "product": "WaterWolf",
        "transforms": {
            "rule1": "some notes about that rule"
        }
    }

If no value was found for the field name, return a dictionary with null values.


.. ############################################################################
   Graphics Devices API
   ############################################################################

Graphics Devices
----------------

Used to look up what we know for a certain ``vendor_hex`` and
``adapter_hex``.

When you post you need to send a payload as the body part of the
request.
In curl you do that like this::

  curl -X POST -d '[{"adapter_h...., ]' http://socorro-api/graphics_devices/

The payload needs to a JSON encoded array of dicts that each contain
the following keys:

* ``vendor_hex``
* ``adapter_hex``
* ``vendor_name``
* ``adapter_name``


API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------+
| HTTP method    | GET, POST          |
+----------------+--------------------+
| URL            | /graphics_devices/ |
+----------------+--------------------+


Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

This is only applicable when you do a GET

+-------------+---------------+---------------+-----------------------------------+
| Name        | Type of value | Default value | Description                       |
+=============+===============+===============+===================================+
| vendor_hex  | String        | None          | e.g. ``0x1001``                   |
+-------------+---------------+---------------+-----------------------------------+
| adapter_hex | String        | None          | e.g. ``0x166a``                   |
+-------------+---------------+---------------+-----------------------------------+


Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Return a list of extensions::

    {
        "total": 1,
        "hits": [
            {
                "vendor_hex": "0x1001",
                "adapter_hex": "0x166a",
        "vendor_name": "Logitech",
        "adapter_name": "Webcamera 1x"
            }
        ]
    }


.. ############################################################################
   Job API
   ############################################################################

Job service
-----------

Handle the jobs queue for crash reports processing.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-------+
| HTTP method    | GET   |
+----------------+-------+
| URL            | /job/ |
+----------------+-------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| uuid           | String           | None          | Unique identifier of the|
|                |                  |               | crash report to find.   |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

With a GET HTTP method, the service will return data in the following
form::

    {
        "hits": [
            {
                "id": 1,
                "pathname": "",
                "uuid": "e8820616-1462-49b6-9784-e99a32120201",
                "owner": 3,
                "priority": 0,
                "queueddatetime": "2012-02-29T01:23:45+00:00",
                "starteddatetime": "2012-02-29T01:23:45+00:00",
                "completeddatetime": "2012-02-29T01:23:45+00:00",
                "success": True,
                "message": "Hello"
            }
        ],
        "total": 1
    }


.. ############################################################################
   Platforms API
   ############################################################################

Platforms service
-----------------

Return a list of all OS and their short names.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-------------+
| HTTP method    | GET         |
+----------------+-------------+
| URL            | /platforms/ |
+----------------+-------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

None

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

Return something like::

    {
        'hits': [
            {
                'name': 'Windows',
                'code': 'win'
            },
            {
                'name': 'Linux',
                'code': 'lin'
            }
        ],
        'total': 2
    }


.. ############################################################################
   Priorityjobs API
   ############################################################################

Priorityjobs service
--------------------

Handle the priority jobs queue for crash reports processing.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+----------------+
| HTTP method    | GET, POST      |
+----------------+----------------+
| URL            | /priorityjobs/ |
+----------------+----------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| uuid           | String           | None          | Unique identifier of the|
|                |                  |               | crash report to mark.   |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

None

Return value
^^^^^^^^^^^^

With a GET HTTP method, the service will return data in the following
form::

    {
        "hits": [
            {"uuid": "e8820616-1462-49b6-9784-e99a32120201"}
        ],
        "total": 1
    }

With a POST HTTP method, it will return true if the uuid has been successfully
added to the priorityjobs queue, and false if the uuid is already in the queue
or if there has been a problem.


.. ############################################################################
   Products API
   ############################################################################

Products service
----------------

Return information about product(s) and version(s) depending on the parameters the service is
called with.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+------------+
| HTTP method    | GET        |
+----------------+------------+
| URL            | /products/ |
+----------------+------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^^

+----------+---------------------------+---------------+----------------------------------------+
| Name     | Type of value             | Default value | Description                            |
+==========+===========================+===============+========================================+
| versions | String or list of strings | None          | Several product:version strings can    |
|          |                           |               | be specified, separated by a + symbol. |
+----------+---------------------------+---------------+----------------------------------------+

Return value
^^^^^^^^^^^^

If the service is called with the optional versions parameter, the service returns an object with an array of results
labeled as hits and a total::

    {
        "hits": [
            {
                "is_featured": boolean,
                "throttle": float,
                "end_date": "string",
                "start_date": "integer",
                "build_type": "string",
                "product": "string",
                "version": "string",
                "has_builds": boolean
            }
            ...
        ],
        "total": 1
    }

If the service is called with no parameters, it returns an object containing an
order list of products, a dict where keys are product names and values are a
list of all versions of that product, and the total of all versions returned::

    {
        "products": [
            "Firefox",
            "Thunderbird",
            "Fennec"
        ]
        "hits": {
            "Firefox": [
                {
                    "product": "Firefox",
                    "version": "42",
                    "start_date": "2001-01-01",
                    "end_date": "2099-01-01",
                    "throttle": 10.0
                    "featured": false
                    "release": "Nightly"
                    "has_builds": true
                }
            ],
            "Thunderbird": [
                {}
            ]
        },
        "total": 6
    }

.. ############################################################################
   Products Builds API
   ############################################################################

Products Builds service
-----------------------

Query and update information about builds for products.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-------------------+
| HTTP method    | GET, POST         |
+----------------+-------------------+
| URL            | /products/builds/ |
+----------------+-------------------+

Mandatory GET parameters
^^^^^^^^^^^^^^^^^^^^^^^^

+---------+---------------+---------------+-----------------------------------+
| Name    | Type of value | Default value | Description                       |
+=========+===============+===============+===================================+
| product | String        | None          | Product for which to get nightly  |
|         |               |               | builds.                           |
+---------+---------------+---------------+-----------------------------------+

Optional GET parameters
^^^^^^^^^^^^^^^^^^^^^^^

+------------+---------------+------------------+-----------------------------+
| Name       | Type of value | Default value    | Description                 |
+============+===============+==================+=============================+
| version    | String        | None             | Version of the product for  |
|            |               |                  | which to get nightly builds.|
+------------+---------------+------------------+-----------------------------+
| from_date  | Date          | Now - 7 days     | Date from which to get      |
|            |               |                  | nightly builds.             |
+------------+---------------+------------------+-----------------------------+

GET return value
^^^^^^^^^^^^^^^^

Return an array of objects::

    [
        {
            "product": "string",
            "version": "string",
            "platform": "string",
            "buildid": "integer",
            "build_type": "string",
            "beta_number": "string",
            "repository": "string",
            "date": "string"
        },
        ...
    ]

Mandatory POST parameters
^^^^^^^^^^^^^^^^^^^^^^^^^

+-------------+---------------+---------------+-------------------------------------------------------+
| Name        | Type of value | Default value | Description                                           |
+=============+===============+===============+=======================================================+
| product     | String        | None          | Product for which to add a build.                     |
+-------------+---------------+---------------+-------------------------------------------------------+
| version     | String        | None          | Version for new build, e.g. "10.0".                   |
+-------------+---------------+---------------+-------------------------------------------------------+
| platform    | String        | None          | Platform for new build, e.g. "macosx".                |
+-------------+---------------+---------------+-------------------------------------------------------+
| build_id    | String        | None          | Build ID for new build (YYYYMMDD######).              |
+-------------+---------------+---------------+-------------------------------------------------------+
| build_type  | String        | None          | Type of build, e.g. "Release", "Beta", "Aurora", etc. |
+-------------+---------------+---------------+-------------------------------------------------------+

Optional POST parameters
^^^^^^^^^^^^^^^^^^^^^^^^

+-------------+---------------+---------------+-------------------------------------------------------+
| Name        | Type of value | Default value | Description                                           |
+=============+===============+===============+=======================================================+
| beta_number | String        | None          | Beta number if build_type is "Beta".  Mandatory if    |
|             |               |               | build_type is "Beta", ignored otherwise.              |
+-------------+---------------+---------------+-------------------------------------------------------+
| repository  | String        | ""            | The repository from which this release came.          |
+-------------+---------------+---------------+-------------------------------------------------------+

POST return value
^^^^^^^^^^^^^^^^^


On success, returns a 303 See Other redirect to the newly-added build's API page at::

    /products/builds/product/(product)/version/(version)/


.. ############################################################################
   Releases Featured API
   ############################################################################

Releases Featured service
-------------------------

Handle featured versions of a given product. GET the list of all featured
releases of all products, or GET the list of featured versions of a list of
products. PUT a new list for one or several products.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------------+
| HTTP method    | GET, PUT            |
+----------------+---------------------+
| URL            | /releases/featured/ |
+----------------+---------------------+

GET Optional parameters
^^^^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| products       | List of strings  | None              | Product(s) for which to get featured versions, or nothing to get  |
|                |                  |                   | all featured versions.                                            |
+----------------+------------------+-------------------+-------------------------------------------------------------------+

PUT parameters
^^^^^^^^^^^^^^

The PUT method accepts data of this form::

    product=version,version,version&product2=version

For example::

    Firefox=15.0a1,14.0b1&Fennec=14.0b4

Return value
^^^^^^^^^^^^

PUT will return True if the update of the featured releases went fine, or raise
an error otherwise.

GET will return data like so::

    {
        "hits": {
            "Firefox": ["15.0a1", "13.0"],
            "Thunderbird": ["17.0b5", "10"]
        },
        "total": 4
    }


.. ############################################################################
   Report List API
   ############################################################################

Report List service
-------------------

Return a list of crash reports with a specified signature and filtered by
a wide range of options.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------+
| HTTP method    | GET           |
+----------------+---------------+
| URL            | /report/list/ |
+----------------+---------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                   | Type of value                 | Default value  | Description                                                                                                                                             |
+========================+===============================+================+=========================================================================================================================================================+
| products               | String or list of strings     | '`Firefox`'    | The product we are interested in. (e.g. Firefox, Fennec, Thunderbird… )                                                                                 |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| from                   | Date                          | Now - 7 days   | Search for crashes that happened after this date. Can use the following formats: '`yyyy-MM-dd`', '`yyyy-MM-dd HH:ii:ss`' or '`yyyy-MM-dd HH:ii:ss.S`'.  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| to                     | Date                          | Now            | Search for crashes that happened before this date. Can use the following formats: '`yyyy-MM-dd`', '`yyyy-MM-dd HH:ii:ss`' or '`yyyy-MM-dd HH:ii:ss.S`'. |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| versions               | String or list of strings     | None           | Restring to a specific version of the product. Several versions can be specified, separated by a + symbol.                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| os                     | String or list of strings     | None           | Restrict to an Operating System. (e.g. Windows, Mac, Linux… ) Several versions can be specified, separated by a + symbol.                               |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| reasons                | String or list of strings     | None           | Restricts search to crashes caused by this reason.                                                                                                      |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| release_channels       | String or list of strings     | None           | Restricts search to crashes with these release channels.                                                                                                |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_ids             | Integer or list of integers   | None           | Restricts search to crashes that happened on a product with this build ID.                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_from            | Integer or list of integers   | None           | Restricts search to crashes with a build id greater than this.                                                                                          |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_to              | Integer or list of integers   | None           | Restricts search to crashes with a build id lower than this.                                                                                            |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_process        | String                        | '`any`'        | Can be '`any`', '`browser`' or '`plugin`'.                                                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_type           | String                        | '`any`'        | Can be '`any`', '`crash`' or '`hang`'.                                                                                                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_in             | String or list of strings     | '`name`'       | Search for a plugin in this field. '`report\_process`' has to be set to '`plugin`'.                                                                     |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_search\_mode   | String                        | '`default`'    | How to search for this plugin. report\_process has to be set to plugin. Can be either '`default`', '`is\_exactly`', '`contains`' or '`starts\_with`'.   |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_terms          | String or list of strings     | None           | Terms to search for. Several terms can be specified, separated by a + symbol. report\_process has to be set to plugin.                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| result\_number         | Integer                       | 100            | Number of results to return.                                                                                                                            |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| result\_offset         | Integer                       | 0              | Offset of the first result to return.                                                                                                                   |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+

Return value
^^^^^^^^^^^^

In normal cases, return something like this::

    {
        "hits": [
            {
                "client_crash_date": "2011-03-16 13:55:10.0",
                "dump": "...",
                "signature": "arena_dalloc_small | arena_dalloc | free | CloseDir",
                "process_type": null,
                "id": 231224257,
                "hangid": null,
                "version": "4.0b13pre",
                "build": "20110314162350",
                "product": "Firefox",
                "os_name": "Mac OS X",
                "date_processed": "2011-03-16 06:54:56.385843",
                "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                "address": "0x1d3aff03",
                "...": "..."
            },
            {
                "client_crash_date": "2011-03-16 11:35:37.0",
                "...": "..."
            }
        ],
        "total": 2
    }

If `signature` is empty or nonexistent, raise a ``BadRequest`` error.

If another error occured, the API will return a 500 Internal Error HTTP header.


.. ############################################################################
   Search API
   ############################################################################

Search service
--------------

Search for crashes according to a large number of parameters and return
a list of crashes or a list of distinct signatures.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------------+
| HTTP method    | GET                 |
+================+=====================+
| URL            | /search/signatures/ |
+----------------+---------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+--------------------+
| Name           | Type of value    | Default value     | Description        |
+================+==================+===================+====================+
| data\_type     | String           | '`signatures`'    | Type of data we    |
|                |                  |                   | are looking for.   |
|                |                  |                   | Can be '`crashes`' |
|                |                  |                   | or '`signatures`'. |
+----------------+------------------+-------------------+--------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                   | Type of value                 | Default value  | Description                                                                                                                                             |
+========================+===============================+================+=========================================================================================================================================================+
| for                    | String or list of strings     | None           | Terms we are searching for. Each term must be URL encoded. Several terms can be specified, separated by a + symbol.                                     |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| products               | String or list of strings     | '`Firefox`'    | The product we are interested in. (e.g. Firefox, Fennec, Thunderbird… )                                                                                 |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| from                   | Date                          | Now - 7 days   | Search for crashes that happened after this date. Can use the following formats: '`yyyy-MM-dd`', '`yyyy-MM-dd HH:ii:ss`' or '`yyyy-MM-dd HH:ii:ss.S`'.  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| to                     | Date                          | Now            | Search for crashes that happened before this date. Can use the following formats: '`yyyy-MM-dd`', '`yyyy-MM-dd HH:ii:ss`' or '`yyyy-MM-dd HH:ii:ss.S`'. |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| in                     | String or list of strings     | All            | Fields we are searching in. Several fields can be specified, separated by a + symbol. This is NOT implemented for PostgreSQL.                           |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| versions               | String or list of strings     | None           | Restring to a specific version of the product. Several versions can be specified, separated by a + symbol.                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| os                     | String or list of strings     | None           | Restrict to an Operating System. (e.g. Windows, Mac, Linux… ) Several versions can be specified, separated by a + symbol.                               |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| search\_mode           | String                        | '`default`'    | Set how to search. Can be either '`default`', '`is\_exactly`', '`contains`' or '`starts\_with`'.                                                        |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| reasons                | String or list of strings     | None           | Restricts search to crashes caused by this reason.                                                                                                      |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| release_channels       | String or list of strings     | None           | Restricts search to crashes with these release channels.                                                                                                |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build_ids              | Integer or list of integers   | None           | Restricts search to crashes that happened on a product with this build ID.                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_from            | Integer or list of integers   | None           | Restricts search to crashes with a build id greater than this.                                                                                          |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_to              | Integer or list of integers   | None           | Restricts search to crashes with a build id lower than this.                                                                                            |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_process        | String                        | '`any`'        | Can be '`any`', '`browser`' or '`plugin`'.                                                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_type           | String                        | '`any`'        | Can be '`any`', '`crash`' or '`hang`'.                                                                                                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_in             | String or list of strings     | '`name`'       | Search for a plugin in this field. '`report\_process`' has to be set to '`plugin`'.                                                                     |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_search\_mode   | String                        | '`default`'    | How to search for this plugin. report\_process has to be set to plugin. Can be either '`default`', '`is\_exactly`', '`contains`' or '`starts\_with`'.   |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_terms          | String or list of strings     | None           | Terms to search for. Several terms can be specified, separated by a + symbol. report\_process has to be set to plugin.                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| result\_number         | Integer                       | 100            | Number of results to return.                                                                                                                            |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| result\_offset         | Integer                       | 0              | Offset of the first result to return.                                                                                                                   |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+

Return value
^^^^^^^^^^^^

If `data_type` is `crashes`, return value looks like::

    {
        "hits": [
            {
                "count": 1,
                "signature": "arena_dalloc_small | arena_dalloc | free | CloseDir",
            },
            {
                "count": 1,
                "signature": "XPCWrappedNativeScope::TraceJS(JSTracer*, XPCJSRuntime*)",
                "is_solaris": 0,
                "is_linux": 0,
                "numplugin": 0,
                "is_windows": 0,
                "is_mac": 0,
                "numhang": 0
            }
        ],
        "total": 2
    }

If `data_type` is `signatures`, return value looks like::

    {
        "hits": [
            {
                "client_crash_date": "2011-03-16 13:55:10.0",
                "dump": "...",
                "signature": "arena_dalloc_small | arena_dalloc | free | CloseDir",
                "process_type": null,
                "id": 231224257,
                "hangid": null,
                "version": "4.0b13pre",
                "build": "20110314162350",
                "product": "Firefox",
                "os_name": "Mac OS X",
                "date_processed": "2011-03-16 06:54:56.385843",
                "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                "address": "0x1d3aff03",
                "...": "..."
            }
        ],
        "total": 1
    }

If an error occured, the API will return something like this::

    Well, for the moment it doesn't return anything but an Internal Error
    HTTP header... We will improve that soon! :)


.. ############################################################################
   Server Status API
   ############################################################################

Server Status service
---------------------

Return the current state of the server and the revisions of Socorro and
Breakpad.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------+
| HTTP method    | GET             |
+----------------+-----------------+
| URL            | /server_status/ |
+----------------+-----------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

None

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------+---------------+----------------+--------------------------------+
| Name     | Type of value | Default value  | Description                    |
+==========+===============+================+================================+
| duration | Integer       | 12             | Number of lines of data to get.|
+----------+---------------+----------------+--------------------------------+

Return value
^^^^^^^^^^^^

Return a list of data about the server status at different recent times
(usually the status is updated every 15 minutes), and the current version of
Socorro and Breakpad::

    {
        "hits": [
            {
                "id": 1,
                "date_recently_completed": "2000-01-01T00:00:00+00:00",
                "date_oldest_job_queued": "2000-01-01T00:00:00+00:00",
                "avg_process_sec": 2,
                "avg_wait_sec": 5,
                "waiting_job_count": 3,
                "processors_count": 2,
                "date_created": "2000-01-01T00:00:00+00:00"
            }
        ],
        "socorro_revision": 42,
        "breakpad_revision": 43,
        "total": 1
    }


.. ############################################################################
   Signature Summary API (8 of them)
   ############################################################################

Signature Summary service
-------------------------

Return data about a signature. Lots of different reports can be returned,
depending on the value of the ``report_type`` parameter.

API specifications
^^^^^^^^^^^^^^^^^^

The spec is the same for all Signature Summary based services.

+-------------+--------------------+
| HTTP method | GET                |
+=============+====================+
| URL         | /signaturesummary/ |
+-------------+--------------------+

Architecture Signature Summary service
--------------------------------------

Return architectures for a particular signature.

``report_type=architecture``

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String or list of strings     | None           | Restring to a specific version of the product. Several  |
|                |                               |                | versions can be specified, separated by a + symbol.     |
+----------------+-------------------------------+----------------+---------------------------------------------------------+


Return value
^^^^^^^^^^^^

Will return a set of `hits` and a `total` count of elements::

    {
        "hits": [{
            "category": 'amd64',
            "report_count": 1.0,
            "percentage": 100.0,
        }],
        "total": 1,
    }

Exploitability Signature Summary
--------------------------------

Return exploitability for a particular signature.

``report_type=exploitability``

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String or list of strings     | None           | Restring to a specific version of the product. Several  |
|                |                               |                | versions can be specified, separated by a + symbol.     |
+----------------+-------------------------------+----------------+---------------------------------------------------------+


Return value
^^^^^^^^^^^^

Will return a set of `hits` and a `total` count of elements::

    {
        "hits":[{
                'low_count': 3,
                'high_count': 5,
                'null_count': 1,
                'none_count': 2,
                'report_date': yesterday_str,
                'medium_count': 4,
        }],
        "total": 1,
    }


Flash Version Signature Summary service
---------------------------------------

Return flash versions for a particular signature.

``report_type=flash_version``

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String or list of strings     | None           | Restring to a specific version of the product. Several  |
|                |                               |                | versions can be specified, separated by a + symbol.     |
+----------------+-------------------------------+----------------+---------------------------------------------------------+


Return value
^^^^^^^^^^^^

Will return a set of `hits` and a `total` count of elements::

    {
        "hits": [{
            "category": '1.0',
            "report_count": 1.0,
            "percentage": 100.0,
        }],
        "total": 1,
    }


Distinct Install Signature Summary service
------------------------------------------

Return distinct installs calculated for a particular signature.

``report_type=distinct_install``

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String or list of strings     | None           | Restring to a specific version of the product. Several  |
|                |                               |                | versions can be specified, separated by a + symbol.     |
+----------------+-------------------------------+----------------+---------------------------------------------------------+


Return value
^^^^^^^^^^^^

Will return a set of `hits` and a `total` count of elements::

    {
        "hits": [{
            "product_name": 'Firefox',
            "version_string": '8.0',
            "crashes": 10,
            "installations": 8,
        }],
        "total": 1,
    }

Operating System Signature Summary service
------------------------------------------

Return operating systems detected in crashes for a particular signature.

``report_type=os``

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String or list of strings     | None           | Restring to a specific version of the product. Several  |
|                |                               |                | versions can be specified, separated by a + symbol.     |
+----------------+-------------------------------+----------------+---------------------------------------------------------+


Return value
^^^^^^^^^^^^

Will return a set of `hits` and a `total` count of elements::

    {
        "hits": [{
            "category": 'Windows NT 6.4',
            "report_count": 1,
            "percentage": 100.0,
        }],
        "total": 1,
    }

Process Type Signature Summary service
--------------------------------------

Return process types detected in crashes for a particular signature.

``report_type=process_type``

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String or list of strings     | None           | Restring to a specific version of the product. Several  |
|                |                               |                | versions can be specified, separated by a + symbol.     |
+----------------+-------------------------------+----------------+---------------------------------------------------------+


Return value
^^^^^^^^^^^^

Will return a set of `hits` and a `total` count of elements::

    {
        "hits": [{
            "category": 'plugin',
            "report_count": 1,
            "percentage": 100.0,
        }],
        "total": 1,
    }

Products Signature Summary service
----------------------------------

Return products detected for crashes for a particular signature.

``report_type=products``

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String or list of strings     | None           | Restring to a specific version of the product. Several  |
|                |                               |                | versions can be specified, separated by a + symbol.     |
+----------------+-------------------------------+----------------+---------------------------------------------------------+


Return value
^^^^^^^^^^^^

Will return a set of `hits` and a `total` count of elements::

    {
        "hits": [{
            "product_name": 'Firefox',
            "version_string": "8.0",
            "report_count": 1.0,
            "percentage": 100.0,
        }],
        "total": 1,
    }


Uptime Signature Summary service
--------------------------------

Return uptime ranges detected for crashes for a particular signature.

``report_type=uptime``

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signature      | String           | None          | Signature of crash      |
|                |                  |               | reports to get.         |
+----------------+------------------+---------------+-------------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String or list of strings     | None           | Restring to a specific version of the product. Several  |
|                |                               |                | versions can be specified, separated by a + symbol.     |
+----------------+-------------------------------+----------------+---------------------------------------------------------+


Return value
^^^^^^^^^^^^

Will return a set of `hits` and a `total` count of elements::

    {
        "hits": [{
            "category": '15-30 minutes',
            "report_count": 1,
            "percentage": 100.0,
        }],
        "total": 1,
    }


.. ############################################################################
   Signature URLs API
   ############################################################################

Signature URLs service
----------------------

Returns a list of urls for a specific signature, product(s), version(s)s as well as start and end date. Also includes
the total number of times this URL has been reported for the parameters specified above.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------+
| HTTP method    | GET             |
+----------------+-----------------+
| URL            | /signatureurls/ |
+----------------+-----------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| signature      | String           | None              | The signature for which urls shoud be found                       |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| start_date     | Date             | None              | Date from which to collect urls                                   |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| end_date       | Date             | None              | Date up to, but not including, for which urls should be collected |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| products       | String           | None              | Product(s) for which to find urls or, you can send the keyword    |
|                |                  |                   | 'ALL' to get results for all products. Products and 'ALL' cannot  |
|                |                  |                   | be mixed                                                          |
+----------------+------------------+-------------------+-------------------------------------------------------------------+
| versions       | String           | None              | Version(s) for the above products to find urls for or, you can    |
|                |                  |                   | send the keyword 'ALL' to get results for all versions of the     |
|                |                  |                   | selected products. Versions and 'ALL' cannot be mixed             |
+----------------+------------------+-------------------+-------------------------------------------------------------------+

Return value
^^^^^^^^^^^^

Returns an object with a list of urls and the total count for each, as well as a counter,
'total', for the total number of results in the result set::

    {
        "hits": [
            {
                "url": "about:blank",
                "crash_count": 1936
            },
            {
                "..."
            }
        ],
        "total": 1
    }


.. ############################################################################
   Skiplist service API
   ############################################################################

Skiplist service
----------------

Return all skiplist category and rules. The query can be optionally filtered.
Without specifying 'category' or 'rule' you get all. You can filter only by,
for example 'category' by adding '/category/<MyCategory>'.

When doing a POST, both 'category' and 'rule' are mandatory. These parameters
must be posted as form data. E.g.::

  curl -X POST -d category=X -d rule=Y http://socorro-api/bpapi/skiplist/

Also, when you do a delete both 'category' and 'rule' are mandatory. E.g.::

  curl -X DELETE http://socorro-api/bpapi/skiplist/category/X/rule/Y/


API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-------------------+
| HTTP method    | GET, POST, DELETE |
+----------------+-------------------+
| URL            | /skiplist/        |
+----------------+-------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

This is only applicable when you do a POST or a DELETE.

+----------+---------------+---------------+-----------------------------------+
| Name     | Type of value | Default value | Description                       |
+==========+===============+===============+===================================+
| category | String        | None          | e.g. ``prefix``                   |
+----------+---------------+---------------+-----------------------------------+
| date     | String        | None          | e.g. ``__JsCrashMin.*?``          |
+----------+---------------+---------------+-----------------------------------+


Optional parameters
^^^^^^^^^^^^^^^^^^^

Both 'category' and 'rule' are optional when doing a GET.

Return value
^^^^^^^^^^^^

Return a list of extensions::

    {
        "total": 2,
        "hits": [
            {
                "category": "prefix",
                "rule": "JsCrashMin"
            },
            {
                "category": "suffix",
                "rule": "arena_.*"
            },
        ]
    }


.. ############################################################################
   Supersearch Fields API
   ############################################################################

Supersearch Fields service
--------------------------

Returns the list of all the fields that are known to be in the elasticsearch
database.

The data returned by this service is used to generate:
    * the list of parameters the ``/supersearch/`` middleware service accepts ;
    * the list of parameters the SuperSearch django model accepts ;
    * the list of fields that can be used in the Super Search page ;
    * and the mapping of the crashes that are inserted into elasticsearch.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+----------------------+
| HTTP method    | GET                  |
+----------------+----------------------+
| URL            | /supersearch/fields/ |
+----------------+----------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

None.

Optional parameters
^^^^^^^^^^^^^^^^^^^

None.

Return value
^^^^^^^^^^^^

Returns a dictionary of ``field_name:field_data``, in this format::

    {
        "signature": {
            "data_validation_type": "str",
            "default_value": null,
            "form_field_choices": null,
            "form_field_type": "StringField",
            "has_full_version": true,
            "in_database_name": "signature",
            "is_exposed": true,
            "is_mandatory": false,
            "is_returned": true,
            "name": "signature",
            "namespace": "processed_crash",
            "permissions_needed": [],
            "query_type": "string",
            "storage_mapping": {
                "type": "string"
            }
        }
    }



.. ############################################################################
   Suspicious Crash Signatures API
   ############################################################################

Suspicious Crash Signatures service
-----------------------------------

Returns crashes that are explosive/suspicious. These crashes should be examined
by people to make sure there are no regressions in product code base.

Crash signatures are explosive if the count shot up by a huge amount.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------+
| HTTP method    | GET          |
+----------------+--------------+
| URL            | /suspicious/ |
+----------------+--------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

None.

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+--------------------+
| Name           | Type of value    | Default value     | Description        |
+================+==================+===================+====================+
| start_date     | Date             | Today             | The start date to  |
|                |                  |                   | get signatures     |
|                |                  |                   | from.              |
+----------------+------------------+-------------------+--------------------+
| end_date       | Date             | Tomorrow          | The end date to    |
|                |                  |                   | get signatures     |
|                |                  |                   | to. Note that the  |
|                |                  |                   | return value does  |
|                |                  |                   | not include        |
|                |                  |                   | signatures on the  |
|                |                  |                   | end_date           |
+----------------+------------------+-------------------+--------------------+

Return value
^^^^^^^^^^^^

Returns in this format::

    {
        "hits": [
          {"date": date,
           "signatures": [signature1, signature2]},
         ...
        ],
        "total": <number of records returned>
    }

Where ``date`` is in the format of ``YYYY-MM-DD`` and signatures are the raw
strings of the signatures.


.. ############################################################################
   Debug
   ############################################################################

Forcing an implementation
-------------------------

For debuging reasons, you can add a parameter to force the API to use a
specific implementation module. That module must be inside `socorro.external`
and contain the needed service implementation.

+-----------------+---------------+---------------+---------------------------+
| Name            | Type of value | Default value | Description               |
+=================+===============+===============+===========================+
| _force_api_impl | String        | None          | Force the service to use  |
|                 |               |               | a specific module.        |
+-----------------+---------------+---------------+---------------------------+

For example, if you want to force search to be executed with ElasticSearch,
you can add to the middleware call `force\_api\_impl/elasticsearch/`. If
`socorro.external.es` exists and contains a `search` module, it
will get loaded and used.
