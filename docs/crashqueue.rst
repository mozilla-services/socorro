.. _crashqueue-chapter:

====================================
Crash queue: API and Implementations
====================================

The collector and webapp publish crash ids to queues that the processor
consumes to know which crash reports to process.

Socorro has three queues:

* standard: for all incoming crash reports from the collector
* priority: for crash reports that need to be processed *right now*
* reprocessing: for crash reports that a user has asked to be reprocessed


socorro.external.crashqueue_base
================================

* `CrashQueueBase` defines the API for crash queue classes.


socorro.external.pubsub
=======================

**socorro.external.pubsub.crashqueue**

Classes:

* `PubSubCrashQueue`: Handles pulling crash ids from Google Pub/Sub
  subscriptions for processing.

  Also handles publishing crash ids to Google Pub/Sub topics.
