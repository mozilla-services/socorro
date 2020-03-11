.. _collector-chapter:

=========
Collector
=========

The collector's job is to collect incoming crash reports, generate crash ids,
save that data to AWS S3 as soon as possible, and publish a crash report id
to AWS SQS for processing.

Antenna is the name of the collector that we're using now.

For more information on running and configuring Antenna, see the `Antenna docs
<https://antenna.readthedocs.io/>`_.
