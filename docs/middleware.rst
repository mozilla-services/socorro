.. index:: middleware

.. _middleware-chapter:

Middleware API
==============

Search
------

Search for crashes according to a large number of parameters and return
a list of crashes or a list of distinct signatures.

API specifications
^^^^^^^^^^^^^^^^^^

+----------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| HTTP method    | GET                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
+----------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| URL schema     | /search/(data_type)/(optional_parameters)                                                                                                                                                                                                                                                                                                                                                                                                                    |
+----------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Full URL       | /search/(data_type)/for/(terms)/product/(product)/from/(from_date)/to/(to_date)/in/(fields)/version/(version)/os/(os_name)/branches/(branches)/search_mode/(search_mode)/reason/(crash_reason)/build/(build_id)/build_from/(build_from)/build_to/(build_to)/report_process/(report_process)/report_type/(report_type)/plugin_in/(plugin_in)/plugin_search_mode/(plugin_search_mode)/plugin_term/(plugin_term)/result_number/(number)/result_offset/(offset)/ |
+----------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Example        | http://socorro-api/bpapi/search/crashes/for/libflash.so/in/signature/product/firefox/version/4.0.1/from/2011-05-01/to/2011-05-05/os/Windows/                                                                                                                                                                                                                                                                                                                 |
+----------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Mandatory parameters
^^^^^^^^^^^^^^^^^^^^

+----------------+------------------+-------------------+--------------------+
| Name           | Type of value    | Default value     | Description        |
+================+==================+===================+====================+
| data_type      | String           | `signatures`      | Type of data we    |
|                |                  |                   | are looking for.   |
|                |                  |                   | Can be `crashes`   |
|                |                  |                   | or `signatures`.   |
+----------------+------------------+-------------------+--------------------+

Optional parameters
^^^^^^^^^^^^^^^^^^^

+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                   | Type of value                 | Default value  | Description                                                                                                                                             |
+========================+===============================+================+=========================================================================================================================================================+
| for                    | String or list of strings     | None           | Terms we are searching for. Each term must be URL encoded. Several terms can be specified, separated by a + symbol.                                     |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| product                | String or list of strings     | \`Firefox\`    | The product we are interested in. (e.g. Firefox, Fennec, Thunderbird… )                                                                                 |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| from                   | Date                          | Now - 7 days   | Search for crashes that happened after this date. Can use the following formats: “yyyy-MM-dd”, “yyyy-MM-dd HH:ii:ss” or “yyyy-MM-dd HH:ii:ss.S”.        |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| to                     | Date                          | Now            | Search for crashes that happened before this date. Can use the following formats: “yyyy-MM-dd”, “yyyy-MM-dd HH:ii:ss” or “yyyy-MM-dd HH:ii:ss.S”.       |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| in                     | String or list of strings     | All            | Fields we are searching in. Several fields can be specified, separated by a + symbol. This is NOT implemented for PostgreSQL.                           |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| version                | String or list of strings     | None           | Restring to a specific version of the product. Several versions can be specified, separated by a + symbol.                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| os                     | String or list of strings     | None           | Restrict to an Operating System. (e.g. Windows, Mac, Linux… ) Several versions can be specified, separated by a + symbol.                               |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| branches               | String or list of strings     | None           | Restrict to a branch of the product. Several branches can be specified, separated by a + symbol.                                                        |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| search\_mode           | String                        | \`default\`    | Set how to search. Can be either \`default\`, \`is\_exactly\`, \`contains\` or \`starts\_with\`.                                                        |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| reason                 | String or list of strings     | None           | Restricts search to crashes caused by this reason.                                                                                                      |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build                  | Integer or list of integers   | None           | Restricts search to crashes that happened on a product with this build ID.                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_from            | Integer or list of integers   | None           | Restricts search to crashes with a build id greater than this.                                                                                          |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| build\_to              | Integer or list of integers   | None           | Restricts search to crashes with a build id lower than this.                                                                                            |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_process        | String                        | \`any\`        | Can be \`any\`, \`browser\` or \`plugin\`.                                                                                                              |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| report\_type           | String                        | \`any\`        | Can be \`any\`, \`crash\` or \`hang\`.                                                                                                                  |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_in             | String or list of strings     | \`name\`       | Search for a plugin in this field. \`report\_process\` has to be set to \`plugin\`.                                                                     |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_search\_mode   | String                        | \`default\`    | How to search for this plugin. report\_process has to be set to plugin. Can be either \`default\`, \`is\_exactly\`, \`contains\` or \`starts\_with\`.   |
+------------------------+-------------------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------+
| plugin\_term           | String or list of strings     | None           | Terms to search for. Several terms can be specified, separated by a + symbol. report\_process has to be set to plugin.                                  |
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
                ...
            },
            ...
        ],
        "total": 2
    }

If an error occured, the API will return something like this::

    Well, for the moment it doesn't return anything but an Internal Error
    HTTP header... We will improve that soon! :)

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
| Full URL       | /util/versions_info/version/(version)/                                         |
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
            "version_string": "string",
            "product_name": "string",
            "major_version": "string" or None,
            "release_channel": "string" or None,
            "build_id": [list, of, decimals] or None
        }
    }

Forcing an implementation
-------------------------

For debuging reasons, you can add a parameter to force the API to use a
specific implementation module. That module must be inside *socorro.external*
and contain the needed service implementation.

+----------------+---------------+---------------+---------------------------+
| Name           | Type of value | Default value | Description               |
+================+===============+===============+===========================+
| force_api_impl | String        | None          | Force the service to use  |
|                |               |               | a specific module.        |
+----------------+---------------+---------------+---------------------------+

For example, if you want to force search to be executed with ElasticSearch,
you can add to the middleware call \`force_api_impl/elasticsearch/\`. If
*socorro.external.elasticsearch* exists and contains a \`search\` module, it
will get loaded and used.
