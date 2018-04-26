.. _elasticsearch-chapter:

============================
Crash storage: Elasticsearch
============================

Features
========

Socorro uses Elasticsearch as a back-end for several intensive features in the
web app. Here is a list of those features:

* **Super Search**

  Probably the most important one, Super Search is an improved search page
  that allows users to search through any field they like in the database. It
  exposes convenient and powerful operators and allows to build complex
  queries. It is also accessible via the public API, allowing users to build
  their own tools.

  Example: https://crash-stats.mozilla.com/search/

* **Custom Queries**

  Based on Super Search, this feature allows users to write JSON queries that
  are executed directly against Elasticsearch. This is a very sensitive
  feature that gives unrestricted access to your data. Specific permissions
  are needed for users to have access to it.

  Example: nope, this is not publicly accessible :)

* **Signature Report**

  A replacement for the old ``/report/list/`` page. It is heavily based
  on Super Search, and provides useful information about crashes that
  share a signature. Features include listing crash reports, listing user
  comments and showing aggregation on any field of the database.

  Example: https://crash-stats.mozilla.com/signature/?signature=nsTimeout::~nsTimeout%28%29

* **Profile page**

  On the profile page, Super Search is used to show the recent crash
  reports that contain the user's email address.

  Example: https://crash-stats.mozilla.com/profile/


Supported versions of Elasticsearch
===================================

Socorro currently requires Elasticsearch version 1.4.


Configuration
=============

You can see Elasticsearch common options by passing ``--help`` to the
processor app and looking at the ``resource.elasticsearch`` options like
this::

  $ docker-compose run processor bash
  app@processor:/app$ python ./socorro/processor/processor_app \
      --destination.crashstorage_class=socorro.external.es.crashstorage.ESCrashStorage \
      --help


As of this writing, it looks like this::

  --resource.elasticsearch.elasticsearch_class
    (default: socorro.external.es.connection_context.ConnectionContext)

  --resource.elasticsearch.elasticsearch_connection_wrapper_class
    a classname for the type of wrapper for ES connections
    (default: socorro.external.es.connection_context.Connection)

  --resource.elasticsearch.elasticsearch_doctype
    the default doctype to use in elasticsearch
    (default: crash_reports)

  --resource.elasticsearch.elasticsearch_index
    an index format to pull crashes from elasticsearch (use datetime's strftime format to have daily, weekly or monthly indexes)
    (default: socorro%Y%W)

  --resource.elasticsearch.elasticsearch_timeout
    the time in seconds before a query to elasticsearch fails
    (default: 30)

  --resource.elasticsearch.elasticsearch_timeout_extended
    the time in seconds before a query to elasticsearch fails in restricted sections
    (default: 120)

  --resource.elasticsearch.elasticsearch_urls
    the urls to the elasticsearch instances
    (default: http://elasticsearch:9200)


Validate your configuration
---------------------------

The best way to verify you have correctly configured your application for
Elasticsearch is to send it a crash report and verify it is indexed. Follow the
steps in :ref:`processor-chapter` to process a crash in your system. Once it is
processed, verify that your Elasticsearch instance has the data:

::

    $ curl -XGET localhost:9200/socorroYYYYWW/crash_reports/_count


By default, the indices used by Socorro are ``socorroYYYYWW``, so make sure you
get this part right depending on your configuration and the current date.

If you want to use the Web app the check your data, the best way is to go to the
Super Search page (you need to switch it on) and hit the Search button with no
parameter. That should return all the crash reports that were indexed in the
passed week.


Super Search fields
===================

Super Search, and thus all the features based on it, is powered by a master list
of fields that tells it what data to expose and how to expose it. That list
contains data about each field from Elasticsearch that can be manipulated.

The list is managed in code in ``socorro/external/es/super_search_fields.py``
as a dict of ``name`` -> ``properties``.


Names
-----

The name of a field is exposed in the Super Search API. This must be unique.


Properties
----------

Here is an explanation of each properties of a field:

**name**
    The name of the field.

**description**
    Brief description of the field.

    This shows up in the `Super Search API documentation
    <https://crash-stats.mozilla.com/documentation/supersearch/api/>`_.

**namespace**
    The dotted name space for the source of the value of this field.

    Examples:

    * ``raw_crash``
    * ``processed_crash``
    * ``processed_crash.json_dump.crashing_thread``

**in_database_name**
    This is the name used to store this field value in Elasticsearch and other
    places.

**query_type**
    Specifies the operators that can be used with this field in Super Search.
    See the list of query types below.

**data_validation_type**
    Specifies how values are validated when passed to filters of this field
    in Super Search.

    Possible values: ``str``, ``enum``, ``bool``, ``int``, ``datetime``,

**permissions_needed**
    Permissions needed for a user to access this field.

**form_field_choices**
    Possible values for this field in the Super Search form.

**is_exposed**
    Is this field exposed as a filter?

**is_returned**
    Is this field returned in results?

**has_full_version**
    Does this field have a full version in Elasticsearch? Enable only if you use
    a multitype field in the storage mapping.

**storage_mapping**
    Mapping that is used in Elasticsearch for this field. See below for more
    information.


We also have these properties:

**default_value**
    The default value for a Super Search filter.

    Always set to ``None``.

**is_mandatory**
    Is this field required to have a value in the Super Search form?

    Always set to ``False``.


Query types
-----------

Here are the operators that will be available for each ``query_type``. Note that
each operator automatically has an opposite version (for example, each field
that has access to the ``contains`` operator also has ``does not contain``).

+----------------------+------------------------------------------------------+
| Query type value     | Operators                                            |
+======================+======================================================+
| enum                 | has terms                                            |
+----------------------+------------------------------------------------------+
| string               | contains, is, starts with, ends with, exists         |
+----------------------+------------------------------------------------------+
| number               | has terms, >, >=, <, <=                              |
+----------------------+------------------------------------------------------+
| date                 | has terms, >, >=, <, <=                              |
+----------------------+------------------------------------------------------+
| bool                 | is true                                              |
+----------------------+------------------------------------------------------+


Storage mapping
---------------

The storage mapping field contains Elasticsearch mapping instructions for the
field.

See `Elasticsearch 1.4 mapping documentation
<https://www.elastic.co/guide/en/elasticsearch/reference/1.4/mapping.html>`_.
