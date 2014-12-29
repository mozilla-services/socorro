.. index:: elasticsearch

.. _elasticsearch-chapter:

ElasticSearch
=============

Features
--------

Socorro uses elasticsearch as a back-end for several intensive features in the
Web app. Here is a list of those features:

* Super Search
    * probably the most important one, Super Search is an improved search page
      that allows users to search through any field they like in the database.
      It exposes convenient and powerful operators and allows to build complex
      queries. It is also accessible via the public API, allowing users to
      build their own tools.
    * *example*: https://crash-stats.mozilla.com/search/
* Custom Queries
    * based on Super Search, this feature allows users to write JSON queries
      that are executed directly against elasticsearch. This is a very
      sensitive feature that gives unrestricted access to your data. Specific
      permissions are needed for users to have access to it.
    * *example*: nope, this is not publicly accessible :)
* Signature Report
    * a replacement for the old ``/report/list/`` page. It is heavily based
      on Super Search, and provides useful information about crashes that
      share a signature. Features include listing crash reports, listing user
      comments and showing aggregation on any field of the database.
    * *example*: https://crash-stats.mozilla.com/signature/?signature=nsTimeout::~nsTimeout%28%29
* Your Crash Reports
    * a very simple page based on Super Search that shows the recent crash
      reports that contain the user's email address.
    * *example*: https://crash-stats.mozilla.com/your-crashes/
* Automatic emails
    * this feature is very specific to Mozilla's needs. It is a cron job that
      regularly send emails to users that crashed. It is based on ExactTarget,
      an emailing service. You will probably need to do some code changes if
      you intend to use it.

Supported versions
------------------

Socorro currently requires **elasticsearch version 0.90.x**. Support for
versions 1.x is planned but not done at the time of writing. For up-to-date
information, please check `bug 1010239`_.

.. _`bug 1010239`: https://bugzilla.mozilla.org/show_bug.cgi?id=1010239

Installation
------------

Installing elasticsearch is well described in this tutorial:
`Setting up elasticsearch`_. Socorro doesn't require any particular
configuration for elasticsearch. It is however likely that you will want to
tweak it to fit your needs, depending on the size of your cluster, the
quantity of data you deal with, etc.

.. _`Setting up elasticsearch`: http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/setup.html

Once elasticsearch is installed, you will want to set up the basic data
required by Socorro. There is a script that will do that for you::

    $ cd scripts && python ./setup_supersearch_app.py

Use the ``--help`` option to see the different parameters you can use. The only
one you should have to change is ``elasticsearch_urls`` to make it reflect
your cluster's URLs. If you are running elasticsearch on localhost:9200, the
previous command should work as is.

This script creates the ``socorro`` index and populates it with some base data
required by Super Search and by the processors to generate the elasticsearch
mappings they use. See the `Master list of fields`_ section for more
information.

Configuration
-------------

Back-end common
^^^^^^^^^^^^^^^

The back-end configuration files lie in the ``./config/`` folder. All
elasticsearch-based services share the same core of options. As for other
resources, it is recommended to put those options in a single file that you
then include in other files.

Here are the important options that you might want to change:

+-----------------------------+-----------------------------------------------+
| Option                      | Description                                   |
+=============================+===============================================+
| elasticsearch_urls          | A list of URLs to your elasticsearch cluster. |
+-----------------------------+-----------------------------------------------+
| elasticsearch_index         | The main index used to store crash reports.   |
|                             | Can be partitioned by date.                   |
+-----------------------------+-----------------------------------------------+
| elasticsearch_default_index | The index used by default when no partitioning|
|                             | is needed.                                    |
+-----------------------------+-----------------------------------------------+

.. note::
   There are more options but they should be self-explanatory. You can see them
   by using the ``--help`` option of any Socorro app that uses elasticsearch.
   For example:
   ``$ python ./socorro/processor/processor_app.py
   --storage_classes=socorro.external.elasticsearch.crashstorage.ElasticSearchCrashStorage
   --help``

Processors
^^^^^^^^^^

Open the config file for processors: ``./config/processor.ini``.
In the ``[destination]`` namespace, look for the option called
``storage_classes``. That key contains the list of storage systems where the
processors will save data. Add ``socorro.external.elasticsearch.crashstorage.\
ElasticSearchCrashStorage`` to that list to make your processors index data in
elasticsearch.

You will then need to add the specific configuration of Elasticsearch in
your ``processor.ini`` file. You can either edit the file manually to add
the correct namespace and options, or you can regenerate the config file::

    $ socorro processor --admin.conf=config/processor.ini --admin.dump_conf=config/processor.ini

Doing so will add the new Elasticsearch namespace and options to your file, filled
with default values. You can then change them to fit your needs, or if you use
a common ini for Elasticsearch, you can replace those options with an include::

    +include('common_elasticsearch.ini')

Middleware
^^^^^^^^^^

You will need to configure your middleware so it has the correct Elasticsearch
values. The file to edit is ``./config/middleware.ini``. If you have a
common Elasticsesarch config file, you can simply include it in the
``[elasticsearch]`` namespace and be done. Otherwise, update the values to
your needs.

Front-end
^^^^^^^^^

Some of the features based on Elasticsearch are hidden behind switches (using
django-waffle). You will need to activate those switches depending on the
features you want to use.

To activate a feature, use the ``manage.py`` tool::

    $ ./webapp-django/manage.py switch <switch-name> [on, off] [--create]

If it's the first time you turn a feature on, you will need to use the
``--create`` option to create the switch.

Here is a list of the switches you need to turn on to use each feature:

+-----------------------+-----------------------------------------------------+
| Feature               | Switches                                            |
+=======================+=====================================================+
| Custom Queries        | supersearch-custom-query                            |
+-----------------------+-----------------------------------------------------+
| Signature report      | signature-report                                    |
+-----------------------+-----------------------------------------------------+

Validate your configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The best way to verify you have correctly configured your application for
Elasticsearch is to send it a crash report and verify it is indexed. Follow the
steps in :ref:`systemtest-chapter` to send a crash to your system. Once it is
received and processed, verify that your Elasticsearch instance has the data::

    $ curl -XGET localhost:9200/socorroYYYYWW/crash_reports/_count

By default, the indices used by Socorro are ``socorroYYYYWW``, so make sure you
get this part right depending on your configuration and the current date.

If you want to use the Web app the check your data, the best way is to go to
the Super Search page (you need to switch it on) and hit the Search button
with no parameter. That should return all the crash reports that were indexed
in the passed week.

Master list of fields
---------------------

Super Search, and thus all the features based on it, is powered by a master
list of fields that tells it what data to expose and how to expose it. That
list contains data about each field from Elasticsearch that can be manipulated.
You can add new fields and edit existing ones from the admin zone of the
Web app, in the Super Search Fields part.

Here is an explanation of each parameter of a field:

+----------------------+------------------------------------------------------+
| Parameter            | Description                                          |
+======================+======================================================+
| name                 | Name of the field, as exposed in the API.            |
|                      | Must be unique.                                      |
+----------------------+------------------------------------------------------+
| in_database_name     | Name of the field in the database.                   |
+----------------------+------------------------------------------------------+
| namespace            | Namespace of the field. Separated with dots.         |
+----------------------+------------------------------------------------------+
| description          | Description of the field, for admins only.           |
+----------------------+------------------------------------------------------+
| query_type           | Defines operators that can be used in Super Search.  |
|                      | See details below.                                   |
+----------------------+------------------------------------------------------+
| data_validation_type | Defines the validation done on values passed to      |
|                      | filers of this field in Super Search.                |
+----------------------+------------------------------------------------------+
| permissions_needed   | Permissions needed from a user to access this field. |
+----------------------+------------------------------------------------------+
| form_field_choices   | Choices offered for filters of that field in the     |
|                      | Super Search form.                                   |
+----------------------+------------------------------------------------------+
| is_exposed           | Is this field exposed as a filter?                   |
+----------------------+------------------------------------------------------+
| is_returned          | Is this field returned in results?                   |
+----------------------+------------------------------------------------------+
| has_full_version     | Does this field have a full version in Elasticsearch?|
|                      | Enable only if you use a multitype field in the      |
|                      | storage mapping.                                     |
+----------------------+------------------------------------------------------+
| storage_mapping      | Mapping that is used in Elasticsearch for this field.|
|                      | See Elasticsearch documentation for more info.       |
+----------------------+------------------------------------------------------+

Here are the operators that will be available for each ``query_type``. Note that
each operator automatically has an opposite version (for example, each field
that has access to the ``contains`` operator also has ``does not contain``).

+----------------------+------------------------------------------------------+
| Query type           | Operators                                            |
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

Moving data (backfilling, reindexing... )
-----------------------------------------

We currently don't provide a generic tool to move data to Elasticsearch. There
is a script that can be used as a base
(``./scripts/elasticsearch_backfill_app.py``), but you might have to update
it depending on your needs.
