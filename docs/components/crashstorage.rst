.. _crashstorage-chapter:

====================================
Crashstorage API and Implementations
====================================

Documentation of our CrashStorage API. This attempts to provide a complete
picture of all the crash storage classes that are provided by Socorro.

Base class implemented in ``socorro/external/crashstorage_base.py``

These are our base classes for all crash storage for Socorro.

.. Warning::

   August 17th, 2017: These docs are outdated.


socorro.external.crashstorage_base
==================================

base class that defines the crash storage API. You implement this when you want
to plug into any of the Socorro backend components

Base class:

* `CrashStorageBase`: Defines ``save_raw_and_processed()``, ``get_raw()``, etc.

Concrete implementation:

* `NullCrashStorage`: Silently ignores everything it is told to do.

Examples of other concrete implementations are: `PostgreSQLCrashStorage`,
`BotoCrashStorage`.

CrashStorage containers for aggregating multiple crash storage implementations:

* `PolyCrashStorage`: Container for other crash storage systems.
* `FallbackCrashStorage`: Container for two other crash storage systems, a
  primary and a secondary. Attempts on the primary, if it fails it will fallback
  to the secondary. In use when we have cutover between data stores. Can be
  heterogeneous, example: S3 + filesystem and use crashmovers to move from
  filesystem into S3 when S3 comes back.
* `PrimaryDeferredStorage`: Container for two different storage systems and a
  predicate function. If predicate is false, store in primary, otherwise store
  in secondary. Usecase: situation where we want crashes to be put somewhere
  else and not be processed.
* `PrimaryDeferredProcessedStorage`: Container for a PrimaryDeferredStorage, but
  there's a third separate storage for Processed crashes. Example: could fork on
  Product.

Helper for PolyCrashStore:

* `PolyCrashStorageError`: Exception for `PolyCrashStorage`.

How we use these:

We use `CrashStorageBase` in our ``socorro/external`` crash storage
implementations. We use `PolyCrashStorage` (and related containers) as a way to
fork "streams of crashes" into different storage engines. Also, the
`CrashStorage` containers can contain each other!

*TODO: Add an attribute to or rename the CrashStorage containers.*


socorro.database.transaction_executor
=====================================

* `TransactionExecutor`: A functor; a default version of a transaction function
  that contains a commit, rollback depending on whether a transaction succeeds
  or fails.

* `TransactionExecutorWithInfiniteBackoff` - will retry a transaction forever as
  long as the failure is a retriable failure. The failures which are retriable
  are defined in 'operational_exceptions' - in the implementation of
  `ConnectionContext` for any `CrashStorageBase` class. Also have
  'conditional_exceptions', where some exceptions are retriable and others are
  not and we have a function ``is_operational_exception`` to test the contents
  of the exception string passed back to determine whether or not we really want
  to retry. ``wait_log_interval`` is the configured value for notifying the
  logger that the backoff system is sleeping, rather than just silently waiting.

* `TransactionExecutorWithLimitedBackoff` - Redefines the ``backoff_generator()``
  to stop after the last emitted ``backoff_delays`` list item.

*TODO: Move this to socorro.external*


connection_context
==================

This is just duck-typed, so we don't have a base class, currently.


About crash storage implementations
===================================

In each of our crash storage implementations, we create: (Found in:
``socorro/external`` directory tree.)

* `crash_data`: implementation of middleware service.

* `crash`: implementation of middleware service.

* `crashstorage`: a fully abstracted method of saving and retrieving crashes.
  An implementation within a external resource directory.

* `connection_context`: a connection Factory in the form of a Functor
  that returns thinly wrapped connections to the resource.

Reasons we have ``connection_context``:

* wrapper for use with ``with``
* pooled connection context - connections held on to, doesn't log out
* to make threading easier to manage

Below we describe the various implementations used by Socorro to store crashes.

This section should help answer these questions:

* What is this class implementing?
* What was the intended use case for the class?
* Which classes may be used together with which Socorro backend apps?


socorro.external.fs
===================

**socorro.external.fs.crashstorage**

Implements Radix Tree storage of crashes in a filesystem. Regular and Legacy
classes need to be used like-with-like, but Dated and non-dated classes should
be compatible.

If you need on-disk queue for crashmovers or processors, use the Dated variety
of the classes. If you are starting fresh, use the non-Legacy modules.

Use cases:

* For Mozilla use by the collectors.
* For other users, you can use this class as your primary storage instead of S3.
  Be sure to implement this in collectors, crashmovers, processors and
  middleware (depending on which components you use in your configuration).

.. Note::

   Because of the slowness of deleting directories created by on-disk, non-SSD
   storage, the collectors do not unlink directories over time. For many
   environments, you will need to periodically unlink directories, possibly by
   entirely wiping out partitions, rather than using `find` or some other UNIX
   utility to delete.

Classes:

* `FSRadixTreeStorage` - Doesn't have a queueing mechanism. Processors can use
  these for local storage that doesn't require any knowledge of queueing.

* `FSDatedRadixTreeStorage` - Use in-filesystem queueing techniques so that we
  know which crashes are new.

* `FSLegacyRadixTreeStorage` - Doesn't have a queueing mechanism. Processors can
  use these for local storage that doesn't require any knowledge of queueing.
  Backwards compatible with `socorro.external.filesystem` (aka the 2009 system).

* `FSLegacyDatedRadixTreeStorage` - In production use on collectors. Use
  in-filesystem queueing techniques so that we know which crashes are new.
  Backwards compatible with `socorro.external.filesystem` (aka the 2009 system).


socorro.external.postgresql
===========================

**socorro.external.postgresql.crashstorage**

* `PostgreSQLCrashStorage`: In Production. `reports` table mapping is a member
  of the class. Needs to be kept in sync with reports schema. For use with a
  processed crash


**socorro.external.postgresql.connection_context**

* `ConnectionContext`: In Production.
* `ConnectionContextPooled`: not in use because we use pgbouncer. Is threadsafe.

`psycopg2` implements all the "connection" semantics we need, so we do not
implement the thin wrapper that ``socorro.external.hb`` and
``socorro.external.rabbitmq`` have.


**socorro.external.postgresql.dbapi2_util**

A set of utilities for wrapping psycopg2 and designed to be handed to
Transactions.

* `single_value_sql`: Give an SQL statement and receive a single value from
  a single column.
* `single_row_sql`: Give an SQL statement and receive a single row.
* `execute_query_iter`: Wraps a cursor in an interator.
* `execute_query_fetchall`: Returns a list of tuples.
* `execute_no_results`: Executes something you know won't return results.


**socorro.external.postgresql.setupdb_app**

This is used by the `Makefile` and ``build.sh`` to create a test database from
scratch.


**socorro.external.postgresql.models**

These contain our canonical schema definitions. This is used by alembic to
create migrations.


**socorro.external.postgresql.raw_sql**

This directory contains all of the stored procedures used by PostgreSQL.


socorro.external.rabbitmq
=========================

**socorro.external.rabbitmq.crashstorage**

* `RabbitMQCrashStorage`: In Production. Only is capable of storing the crash_id
  of a raw_crash. It *could* implement storage of dumps etc, but it is not
  suitable to actually store crashes at this time.


**socorro.external.rabbitmq.connection_context**

* `Connection`: In Production. A thin wrapper around `pika`. Also defines a
  channel and our declared queues (`socorro.normal` and `socorro.priority`). For
  commit/rollback, we just pass.

* `ConnectionContext`: Our factory implemented as a functor that we never use,
  but is a base class for our Pooled connections. If we use this directly, it
  will fail because the connections will close before the processors have a
  chance to have a look and ack.

* `ConnectionContextPooled`: In production. This is implemented as a per-thread
  pool.


**socorro.external.rabbitmq.rmq_new_crash_source**

A pluggable Functor/generator for feeding new crashes to the processor,
implemented as a wrapper around new_crashes().


Which classes are used with which _app
======================================

* `socorro.collector.collector_app`: We currently only use `socorro.external.fs`
  in production. In testing we use `socorro.external.fs` and
  `socorro.external.rabbitmq`.

* `socorro.collector.crashmover_app`: In production: reads from
  `socorro.external.fs`, write to `socorro.external.hb`. In testing we use
  `socorro.external.fs`.

* `socorro.processor.processor_app`: In production: reads from
  `socorro.external.hb`, writes to `socorro.external.es`, `socorro.external.hb`
  and `socorro.external.postgresql` using `PolyCrashStore`. In testing we use
  `socorro.external.fs`, `socorro.external.rabbitmq`, and
  `socorro.external.postgresql`.


Which classes can be used together
==================================

Cannot mix *LegacyRadix* and *Radix* in one system which runs more than one app
and shares a filesystem.


Potential Edicts
================

* Every container has an attribute that describes it as a container!
