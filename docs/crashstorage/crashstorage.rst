.. _crashstorage-chapter:

======================================
Crash storage: API and Implementations
======================================

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

CrashStorage containers for aggregating multiple crash storage implementations:

* `PolyCrashStorage`: Container for other crash storage systems.

Helper for PolyCrashStore:

* `PolyCrashStorageError`: Exception for `PolyCrashStorage`.

How we use these:

We use `CrashStorageBase` in our ``socorro/external`` crash storage
implementations. We use `PolyCrashStorage` (and related containers) as a way to
fork "streams of crashes" into different storage engines. Also, the
`CrashStorage` containers can contain each other!


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

Implements Radix Tree storage of crashes in a filesystem.

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

* `FSPermanentStorage` - Doesn't have a queueing mechanism. Processors can
  use these for local storage that doesn't require any knowledge of queueing.
  Backwards compatible with `socorro.external.filesystem` (aka the 2009 system).


socorro.external.postgresql
===========================

**socorro.external.postgresql.connection_context**

* `ConnectionContext`: In Production.


socorro.external.pubsub
=======================

**socorro.external.pubsub.crashqueue**

Classes:

* `PubSubCrashQueue`: Handles pulling crash ids from Pub/Sub subscriptions for
  processing.

  Also handles publishing crash ids to Pub/Sub topics.
