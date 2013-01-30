.. index:: middleware

.. _middleware-chapter:

Middleware API
==============

API map
-------

New-style, documented services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* `/bugs/ <#bugs>`_
* `/crash/ <#crash>`_
* `/crash_data/ <#crash-data>`_
* /crashes/
    * `/crashes/comments <#crashes-comments>`_
    * `/crashes/daily <#crashes-daily>`_
    * `/crashes/frequency  <#crashes-frequency>`_
    * `/crashes/paireduuid <#crashes-paireduuid>`_
    * `/crashes/signatures <#crashes-signatures>`_
* `/crashtrends/ <#crashtrends>`_
* `/extensions/ <#extensions>`_
* `/job/ <#job>`_
* `/platforms/ <#platforms>`_
* `/priorityjobs/ <#priorityjobs>`_
* `/products/ <#products>`_
* /products/
    * `/products/builds/ <#products-builds>`_
    * `/products/versions/ <#products-versions>`_
* /releases/
    * `/releases/featured/ <#releases-featured>`_
* /report/
    * `/report/list/ <#list-report>`_
* `/signatureurls <#signature-urls>`_
* /search/
    * `/search/crashes/ <#search>`_
    * `/search/signatures/ <#search>`_
* `/server_status/ <#server-status>`_
* /util/
    * `/util/versions_info/ <#versions-info>`_

Old-style, undocumented services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

See source code in ``.../socorro/services/`` for more details.

* /current/versions
* /email
* /emailcampaigns/campaign
* /emailcampaigns/campaigns/page
* /emailcampaigns/create
* /emailcampaigns/subscription
* /emailcampaigns/volume
* /reports/hang
* /schedule/priority/job
* /topcrash/sig/trend/history
* /topcrash/sig/trend/rank


.. ############################################################################
   Bugs API
   ############################################################################

Bugs
----

Return a list of signature - bug id associations.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------------------------------------+
| HTTP method    | POST                                                                              |
+----------------+-----------------------------------------------------------------------------------+
| URL schema     | /bugs/                                                                            |
+----------------+-----------------------------------------------------------------------------------+
| Full URL       | /bugs/                                                                            |
+----------------+-----------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/bugs/ data: signatures=mysignature+anothersig+jsCrashSig |
+----------------+-----------------------------------------------------------------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+---------------+-------------------------+
| Name           | Type of value    | Default value | Description             |
+================+==================+===============+=========================+
| signatures     | List of strings  | None          | Signatures of bugs      |
|                |                  |               | to get.                 |
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
   Crash API
   ############################################################################

Crash
-----

Return a single crash report from its UUID.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------------------------------------+
| HTTP method    | POST                                                                              |
+----------------+-----------------------------------------------------------------------------------+
| URL schema     | /crash/(optional_parameters)                                                      |
+----------------+-----------------------------------------------------------------------------------+
| Full URL       | /crash/uuid/(uuid)/                                                               |
+----------------+-----------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/crash/uuid/58727744-12f5-454a-bcf5-f688af393821/         |
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

Crash Data
----------

Return JSON or binary data of a crash report, given its uuid.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------------------------------------------------------------------------------------+
| HTTP method    | POST                                                                                        |
+----------------+---------------------------------------------------------------------------------------------+
| URL schema     | /crash_data/(optional_parameters)                                                           |
+----------------+---------------------------------------------------------------------------------------------+
| Full URL       | /crash_data/datatype/(datatype)/uuid/(uuid)/                                                |
+----------------+---------------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/crash_data/datatype/raw/uuid/58727744-12f5-454a-bcf5-f688af393821/ |
+----------------+---------------------------------------------------------------------------------------------+

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
   Crashes Comments API
   ############################################################################

Crashes Comments
----------------

Return a list of comments on crash reports, filtered by signatures and other
fields.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                                                                                                                                                                                                                                                                                                                          |
+----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| URL schema     | /crashes/comments/(parameters)                                                                                                                                                                                                                                                                                                                                                               |
+----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Full URL       | /crashes/comments/signature/(signature)/products/(products)/from/(from_date)/to/(to_date)/versions/(versions)/os/(os_name)/reasons/(crash_reason)/build_ids/(build_ids)/build_from/(build_from)/build_to/(build_to)/report_process/(report_process)/report_type/(report_type)/plugin_in/(plugin_in)/plugin_search_mode/(plugin_search_mode)/plugin_terms/(plugin_terms)/ |
+----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/crashes/comments/signature/SocketSend/products/Firefox/versions/Firefox:4.0.1/from/2011-05-01/to/2011-05-05/os/Windows/                                                                                                                                                                                                                                             |
+----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

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

Crashes Daily
-------------

Return crashes by active daily users.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------------------------------------------------------------+
| HTTP method    | GET                                                                            |
+----------------+--------------------------------------------------------------------------------+
| URL schema     | /crashes/daily/(optional_parameters)                                           |
+----------------+--------------------------------------------------------------------------------+
| Full URL       | /crashes/daily/product/(product)/versions/(versions)/from_date/(from_date)/    |
|                | to_date/(to_date)/date_range_type/(date_range_type)/os/(os_names)/             |
|                | report_type/(report_type)/separated_by/(separated_by)/                         |
+----------------+--------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/crashes/daily/product/Firefox/versions/9.0a1+16.0a1/  |
+----------------+--------------------------------------------------------------------------------+

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

Crashes Frequency
-----------------

Return the number and frequency of crashes on each OS.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                                                                                                                                                                                                                                                                                                                           |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| URL schema     | /crashes/frequency/(parameters)                                                                                                                                                                                                                                                                                                                                                               |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Full URL       | /crashes/frequency/signature/(signature)/products/(products)/from/(from_date)/to/(to_date)/versions/(versions)/os/(os_name)/reasons/(crash_reason)/build_ids/(build_ids)/build_from/(build_from)/build_to/(build_to)/report_process/(report_process)/report_type/(report_type)/plugin_in/(plugin_in)/plugin_search_mode/(plugin_search_mode)/plugin_terms/(plugin_terms)/ |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/crashes/frequency/signature/SocketSend/products/Firefox/versions/Firefox:4.0.1/from/2011-05-01/to/2011-05-05/os/Windows/                                                                                                                                                                                                                                             |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

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

Crashes Paireduuid
------------------

Return paired uuid given a uuid and an optional hangid.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+----------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                    |
+----------------+----------------------------------------------------------------------------------------+
| URL schema     | /crashes/paireduuid/(optional_parameters)                                              |
+----------------+----------------------------------------------------------------------------------------+
| Full URL       | /crashes/paireduuid/uuid/(uuid)/hangid/(hangid)/                                       |
+----------------+----------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/crashes/paireduuid/uuid/e8820616-1462-49b6-9784-e99a32120201/ |
+----------------+----------------------------------------------------------------------------------------+

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

Crashes Signatures
------------------

Return top crashers by signatures.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------------------------------------------------------------+
| HTTP method    | GET                                                                            |
+----------------+--------------------------------------------------------------------------------+
| URL schema     | /crashes/signatures/(optional_parameters)                                      |
+----------------+--------------------------------------------------------------------------------+
| Full URL       | /crashes/signatures/product/(product)/version/(version)/to_from/(to_date)/     |
|                | duration/(number_of_days)/crash_type/(crash_type)/limit/(number_of_results)/   |
|                | os/(operating_system)/date_range_type/(date_range_type)/                       |
+----------------+--------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/crashes/signatures/product/Firefox/version/9.0a1/     |
+----------------+--------------------------------------------------------------------------------+

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
   Extensions API
   ############################################################################

Extensions
----------

Return a list of extensions associated with a crash's UUID.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                     |
+----------------+-----------------------------------------------------------------------------------------+
| URL schema     | /extensions/(optional_parameters)                                                       |
+----------------+-----------------------------------------------------------------------------------------+
| Full URL       | /extensions/uuid/(uuid)/date/(crash_date)/                                              |
+----------------+-----------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/extensions/uuid/xxxx-xxxx-xxxx/date/2012-02-29T01:23:45+00:00/ |
+----------------+-----------------------------------------------------------------------------------------+

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
   Crash Trends API
   ############################################################################

Crash Trends
------------

Return a list of nightly or aurora crashes that took place between two dates.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------------------------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                                           |
+----------------+---------------------------------------------------------------------------------------------------------------+
| URL schema     | /crashtrends/(optional_parameters)                                                                            |
+----------------+---------------------------------------------------------------------------------------------------------------+
| Full URL       | /crashtrends/start_date/(start_date)/end_date/(end_date)/product/(product)/version/(version)                  |
+----------------+---------------------------------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/crashtrends/start_date/2012-03-01/end_date/2012-03-15/product/Firefox/version/13.0a1 |
+----------------+---------------------------------------------------------------------------------------------------------------+

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
   Products Builds API
   ############################################################################

Job
---

Handle the jobs queue for crash reports processing.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------------------------------------------------------------+
| HTTP method    | GET                                                                            |
+----------------+--------------------------------------------------------------------------------+
| URL schema     | /job/(parameters)                                                              |
+----------------+--------------------------------------------------------------------------------+
| Full URL       | /job/uuid/(uuid)/                                                              |
+----------------+--------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/job/uuid/e8820616-1462-49b6-9784-e99a32120201/        |
+----------------+--------------------------------------------------------------------------------+

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

Platforms
---------

Return a list of all OS and their short names.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-------------------------------------+
| HTTP method    | GET                                 |
+----------------+-------------------------------------+
| URL schema     | /platforms/                         |
+----------------+-------------------------------------+
| Full GET URL   | /platforms/                         |
+----------------+-------------------------------------+
| GET Example    | http://socorro-api/bpapi/platforms/ |
+----------------+-------------------------------------+

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

Priorityjobs
------------

Handle the priority jobs queue for crash reports processing.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------------------------------------------+
| HTTP method    | GET, POST                                                                               |
+----------------+-----------------------------------------------------------------------------------------+
| URL schema     | /priorityjobs/(parameters)                                                              |
+----------------+-----------------------------------------------------------------------------------------+
| Full GET URL   | /priorityjobs/uuid/(uuid)/                                                              |
+----------------+-----------------------------------------------------------------------------------------+
| GET Example    | http://socorro-api/bpapi/priorityjobs/uuid/e8820616-1462-49b6-9784-e99a32120201/        |
+----------------+-----------------------------------------------------------------------------------------+
| POST Example   | http://socorro-api/bpapi/priorityjobs/, data: uuid=e8820616-1462-49b6-9784-e99a32120201 |
+----------------+-----------------------------------------------------------------------------------------+

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

Products
--------

Return information about product(s) and version(s) depending on the parameters the service is
called with.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------------------------------------------------------------+
| HTTP method    | GET                                                                            |
+----------------+--------------------------------------------------------------------------------+
| URL schema     | /products/(optional_parameters)                                                |
+----------------+--------------------------------------------------------------------------------+
| Full URL       | /products/versions/(versions)                                                  |
+----------------+--------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/products/versions/Firefox:9.0a1/                      |
+----------------+--------------------------------------------------------------------------------+

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

Products Builds
---------------

Query and update information about builds for products.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------------------------------------------------------------+
| HTTP method    | GET, POST                                                                      |
+----------------+--------------------------------------------------------------------------------+
| URL schema     | /products/builds/(optional_parameters)                                         |
+----------------+--------------------------------------------------------------------------------+
| Full URL       | /products/builds/product/(product)/version/(version)/date_from/(date_from)/    |
+----------------+--------------------------------------------------------------------------------+
| GET Example    | http://socorro-api/bpapi/products/builds/product/Firefox/version/9.0a1/        |
| POST Example   | http://socorro-api/bpapi/products/builds/product/Firefox/,                     |
|                | data: version=10.0&platform=macosx&build_id=20120416012345&                    |
|                |       build_type=Beta&beta_number=2&repository=mozilla-central                 |
+----------------+--------------------------------------------------------------------------------+

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

Releases Featured
-----------------

Handle featured versions of a given product. GET the list of all featured
releases of all products, or GET the list of featured versions of a list of
products. PUT a new list for one or several products.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------------------------------------------------------------------------------+
| HTTP method    | GET, PUT                                                                              |
+----------------+---------------------------------------------------------------------------------------+
| URL schema     | /releases/featured/(parameters)                                                       |
+----------------+---------------------------------------------------------------------------------------+
| Full GET URL   | /releases/featured/products/(products)/                                               |
+----------------+---------------------------------------------------------------------------------------+
| Full PUT URL   | /releases/featured/ data: product=version+version+version&product2=version...         |
+----------------+---------------------------------------------------------------------------------------+
| GET Example    | http://socorro-api/bpapi/releases/featured/products/Firefox+Fennec/                   |
+----------------+---------------------------------------------------------------------------------------+
| PUT Example    | http://socorro-api/bpapi/releases/featured/ data: Firefox=15.0a1+14.0b1&Fennec=14.0b4 |
+----------------+---------------------------------------------------------------------------------------+

GET Optional parameters
^^^^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+-------------------------------------------------------------------+
| Name           | Type of value    | Default value     | Description                                                       |
+================+==================+===================+===================================================================+
| products       | List of strings  | None              | Product(s) for which to get featured versions, or nothing to get  |
|                |                  |                   | all featured versions.                                            |
+----------------+------------------+-------------------+-------------------------------------------------------------------+

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
   Signature URLs API
   ############################################################################

Signature URLs
--------------

Returns a list of urls for a specific signature, product(s), version(s)s as well as start and end date. Also includes
the total number of times this URL has been reported for the parameters specified above.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                                                                                                                                  |
+----------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| URL schema     | /signatureurls/(parameters)                                                                                                                                                                          |
+----------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Full URL       | /signatureurls/signature/(signature)/start_date/(start_date)/end_date/(end_date)/products/(products)/versions/(versions)                                                                             |
+----------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/signatureurls/signature/samplesignature/start_date/2012-03-01T00:00:00+00:00/end_date/2012-03-31T00:00:00+00:00/products/Firefox+Fennec/versions/Firefox:4.0.1+Fennec:13.0/ |
+----------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

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
   Search API
   ############################################################################

Search
------

Search for crashes according to a large number of parameters and return
a list of crashes or a list of distinct signatures.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| URL schema     | /search/(data_type)/(optional_parameters)                                                                                                                                                                                                                                                                                                                                                                                                                                 |
+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Full URL       | /search/(data_type)/for/(terms)/products/(products)/from/(from_date)/to/(to_date)/in/(fields)/versions/(versions)/os/(os_name)/search_mode/(search_mode)/reasons/(crash_reasons)/build_ids/(build_ids)/build_from/(build_from)/build_to/(build_to)/report_process/(report_process)/report_type/(report_type)/plugin_in/(plugin_in)/plugin_search_mode/(plugin_search_mode)/plugin_terms/(plugin_terms)/result_number/(number)/result_offset/(offset)/ |
+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/search/crashes/for/libflash.so/in/signature/products/Firefox/versions/Firefox:4.0.1/from/2011-05-01/to/2011-05-05/os/Windows/                                                                                                                                                                                                                                                                                                                    |
+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

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

Server Status
-------------

Return the current state of the server and the revisions of Socorro and
Breakpad.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------+
| HTTP method    | GET                                                 |
+----------------+-----------------------------------------------------+
| URL schema     | /server_status/(parameters)                         |
+----------------+-----------------------------------------------------+
| Full URL       | /server_status/duration/(duration)/                 |
+----------------+-----------------------------------------------------+
| Example        | http://socorro-api/bpapi/server_status/duration/12/ |
+----------------+-----------------------------------------------------+

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
   Report List API
   ############################################################################

List Report
-----------

Return a list of crash reports with a specified signature and filtered by
a wide range of options.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                                                                                                                                                                                                                                                                                                                     |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| URL schema     | /report/list/(parameters)                                                                                                                                                                                                                                                                                                                                                               |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Full URL       | /report/list/signature/(signature)/products/(products)/from/(from_date)/to/(to_date)/versions/(versions)/os/(os_name)/reasons/(crash_reason)/build_ids/(build_ids)/build_from/(build_from)/build_to/(build_to)/report_process/(report_process)/report_type/(report_type)/plugin_in/(plugin_in)/plugin_search_mode/(plugin_search_mode)/plugin_terms/(plugin_terms)/ |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/report/list/signature/SocketSend/products/Firefox/versions/Firefox:4.0.1/from/2011-05-01/to/2011-05-05/os/Windows/                                                                                                                                                                                                                                             |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

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
   Util Versions Info API
   ############################################################################

Versions Info
-------------

Return information about one or several couples product:version.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------------------------------------------------------------+
| HTTP method    | GET                                                                            |
+----------------+--------------------------------------------------------------------------------+
| URL schema     | /util/versions_info/(optional_parameters)                                      |
+----------------+--------------------------------------------------------------------------------+
| Full URL       | /util/versions_info/versions/(versions)/                                       |
+----------------+--------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/util/versions_info/versions/Firefox:9.0a1+Fennec:7.0/ |
+----------------+--------------------------------------------------------------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

None.

Optional parameters
^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+--------------------+
| Name           | Type of value    | Default value     | Description        |
+================+==================+===================+====================+
| versions       | String or list   | None              | Product:Versions   |
|                | of strings       |                   | couples for which  |
|                |                  |                   | information is     |
|                |                  |                   | asked.             |
+----------------+------------------+-------------------+--------------------+

Return value
^^^^^^^^^^^^

If parameter ``versions`` is unvalid, return value is ``None``. Otherwise it
looks like this::

    {
        "product_name:version_string": {
            "product_version_id": integer,
            "version_string": "string",
            "product_name": "string",
            "major_version": "string" or None,
            "release_channel": "string" or None,
            "build_id": [list, of, decimals] or None
        }
    }

.. ############################################################################
   Debug
   ############################################################################

Forcing an implementation
-------------------------

For debuging reasons, you can add a parameter to force the API to use a
specific implementation module. That module must be inside `socorro.external`
and contain the needed service implementation.

+----------------+---------------+---------------+---------------------------+
| Name           | Type of value | Default value | Description               |
+================+===============+===============+===========================+
| force_api_impl | String        | None          | Force the service to use  |
|                |               |               | a specific module.        |
+----------------+---------------+---------------+---------------------------+

For example, if you want to force search to be executed with ElasticSearch,
you can add to the middleware call `force\_api\_impl/elasticsearch/`. If
`socorro.external.elasticsearch` exists and contains a `search` module, it
will get loaded and used.


Adding new Middleware Services
==============================

See this page :ref:`addingmiddleware-chapter` for an introduction to
how to add a new middleware service.
