.. _elasticsearch-chapter:

=============
Elasticsearch
=============

FIXME(willkg): This needs to be updated, overhauled, and reduced.


Features
========

Socorro uses Elasticsearch as a back-end for several intensive features in the
Web app. Here is a list of those features:

* Super Search

  * probably the most important one, Super Search is an improved search page
    that allows users to search through any field they like in the database. It
    exposes convenient and powerful operators and allows to build complex
    queries. It is also accessible via the public API, allowing users to build
    their own tools.

  * Example: https://crash-stats.mozilla.com/search/

* Custom Queries

  * based on Super Search, this feature allows users to write JSON queries that
    are executed directly against Elasticsearch. This is a very sensitive
    feature that gives unrestricted access to your data. Specific permissions
    are needed for users to have access to it.

  * Example: nope, this is not publicly accessible :)

* Signature Report

  * a replacement for the old ``/report/list/`` page. It is heavily based
    on Super Search, and provides useful information about crashes that
    share a signature. Features include listing crash reports, listing user
    comments and showing aggregation on any field of the database.

  * Example: https://crash-stats.mozilla.com/signature/?signature=nsTimeout::~nsTimeout%28%29

* Profile page

  * on the profile page, Super Search is used to show the recent crash
    reports that contain the user's email address.

  * Example: https://crash-stats.mozilla.com/profile/


Supported versions
==================

Socorro currently requires Elasticsearch version 1.4.


Configuration
=============

Back-end common
---------------

The back-end configuration files lie in the ``./config/`` folder. All
Elasticsearch-based services share the same core of options. As for other
resources, it is recommended to put those options in a single file that you then
include in other files.

Here are the important options that you might want to change:

+-----------------------------+-----------------------------------------------+
| Option                      | Description                                   |
+=============================+===============================================+
| elasticsearch_urls          | A list of URLs to your Elasticsearch cluster. |
+-----------------------------+-----------------------------------------------+
| elasticsearch_index         | The main index used to store crash reports.   |
|                             | Can be partitioned by date.                   |
+-----------------------------+-----------------------------------------------+
| elasticsearch_default_index | The index used by default when no partitioning|
|                             | is needed.                                    |
+-----------------------------+-----------------------------------------------+

.. note::
   There are more options but they should be self-explanatory. You can see them
   by using the ``--help`` option of any Socorro app that uses Elasticsearch.
   For example:
   ``$ python ./socorro/processor/processor_app.py
   --storage_classes=socorro.external.es.crashstorage.ESCrashStorage --help``


Processors
----------

Open the config file for processors: ``./config/processor.ini``. In the
``[destination]`` namespace, look for the option called ``storage_classes``.
That key contains the list of storage systems where the processors will save
data. Add ``socorro.external.es.crashstorage.\ ESCrashStorage`` to that list to
make your processors index data in Elasticsearch.

You will then need to add the specific configuration of Elasticsearch in your
``processor.ini`` file. You can either edit the file manually to add the correct
namespace and options, or you can regenerate the config file::

    $ socorro processor --admin.conf=config/processor.ini --admin.dump_conf=config/processor.ini

Doing so will add the new Elasticsearch namespace and options to your file,
filled with default values. You can then change them to fit your needs, or if
you use a common ini for Elasticsearch, you can replace those options with an
include::

    +include('common_elasticsearch.ini')


Front-end
---------

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
|                       | there is no feature behind waffle at the moment     |
+-----------------------+-----------------------------------------------------+

Here are features that are enabled by default, that you need to switch if you
want to *disable* them:

+-----------------------+-----------------------------------------------------+
| Feature               | Switches                                            |
+=======================+=====================================================+
| Custom Queries        | supersearch-custom-query-disabled                   |
+-----------------------+-----------------------------------------------------+


Validate your configuration
---------------------------

The best way to verify you have correctly configured your application for
Elasticsearch is to send it a crash report and verify it is indexed. Follow the
steps in :ref:`systemtest-chapter` to send a crash to your system. Once it is
received and processed, verify that your Elasticsearch instance has the data::

    $ curl -XGET localhost:9200/socorroYYYYWW/crash_reports/_count


By default, the indices used by Socorro are ``socorroYYYYWW``, so make sure you
get this part right depending on your configuration and the current date.

If you want to use the Web app the check your data, the best way is to go to the
Super Search page (you need to switch it on) and hit the Search button with no
parameter. That should return all the crash reports that were indexed in the
passed week.


Fake data for development
=========================

If you want to populate your Elasticsearch database with some fake data, the
recommended way is to first insert fakedata into PostgreSQL and then migrate
that data over to Elasticsearch. This way you will have consistent data accross
both databases and will be able to have comparison points.

To insert fake data into PostgreSQL, see :ref:`databasesetup-chapter`.

When that is complete, run the following script to migrate the data from
PostgreSQL to Elasticsearch::

    $ python socorro/external/postgresql/crash_migration_app.py


Master list of fields
=====================

Super Search, and thus all the features based on it, is powered by a master list
of fields that tells it what data to expose and how to expose it. That list
contains data about each field from Elasticsearch that can be manipulated. You
can add new fields and edit existing ones from the admin zone of the Web app, in
the Super Search Fields part.

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
