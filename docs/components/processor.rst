.. _processor-chapter:

=========
Processor
=========

.. Note::

   We're in the process of extracting the processor out of Socorro as a separate
   project. There's no ETA for that work, yet.


Running the processor
=====================

To run the processor using the processor configuration, do::

  $ docker-compose up processor


That will bring up all the services the processor requires to run and start the
processor using the ``/app/docker/run_processor.sh`` script and the processor
configuration.

To ease debugging in the container, you can run a shell::

  $ docker-compose run processor /bin/bash


Then you can start and stop the processor and tweak files and all that jazz.

.. Note::

   The stackwalk binaries are in ``/stackwalk`` in the container.


Processing crashes
==================

Running the processor is pretty uninteresting since it'll just sit there until
you give it something to process.

In order to process something, you first need to acquire raw crash data, put the
data in the S3 container in the appropriate place, then you need to add the
crash id to the "socorro.normal" RabbitMQ queue.

We have helper scripts for these steps.


``scripts/fetch_crashids.py``
-----------------------------

This will generate a list of crash ids from crash-stats.mozilla.com that meet
specified criteria. Crash ids are printed to stdout, so you can use this in
conjunction with other scripts or redirect to a file.

This pulls 100 crash ids from yesterday for Firefox product::

  $ docker/as_me.sh scripts/fetch_crashids.py

This pulls 5 crash ids from 2017-09-01::

  $ docker/as_me.sh scripts/fetch_crashids.py --num=5 --date=2017-09-01

This pulls 100 crash ids for criteria specified with a Super Search url that we
copy and pasted::

  $ docker/as_me.sh scripts/fetch_crashids.py "--url=https://crash-stats.mozilla.com/search/?product=Firefox&date=%3E%3D2017-09-05T15%3A09%3A00.000Z&date=%3C2017-09-12T15%3A09%3A00.000Z&_sort=-date&_facets=signature&_columns=date&_columns=signature&_columns=product&_columns=version&_columns=build_id&_columns=platform"

You can get command help::

  $ docker/as_me.sh scripts/fetch_crash_data.py --help


``scripts/fetch_crash_data.py``
-------------------------------

This will fetch raw crash data from crash-stats.mozilla.com and save it in the
appropriate directory structure rooted at outputdir.

Usage from host::

  $ docker/as_me.sh scripts/fetch_crash_data.py <outputdir> <crashid> [<crashid> ...]


For example (assumes this crash exists)::

  $ docker/as_me.sh scripts/fetch_crash_data.py ./testdata 5c9cecba-75dc-435f-b9d0-289a50170818


Use with ``scripts/fetch_crashids.py`` to fetch crash data from 100 crashes from
yesterday for Firefox::

  $ docker/as_me.sh bash
  app@...:/app$ scripts/fetch_crashids.py | xargs scripts/fetch_crash_data.py ./testdata


You can get command help::

  $ docker/as_me.sh scripts/fetch_crash_data.py --help


You should run this with ``docker/as_me.sh`` so that the files that get saved to
the file system are owned by the user/group of the account you're using on your
host.

This script requires that you have a valid API token from the
crash-stats.mozilla.com environment that has the "View Raw Dumps" permission.

You can generate API tokens at `<https://crash-stats.mozilla.com/api/tokens/>`_.

Add the API token value to your ``my.env`` file::

    SOCORRO_API_TOKEN=apitokenhere

.. Note::

   Make sure you treat any data you pull from production in accordance with our
   data policies that you agreed to when granted access to it.


``scripts/socorro_aws_s3.sh``
-----------------------------

This script is a convenience wrapper around the aws cli s3 subcommand that uses
Socorro environment variables to set the credentials and endpoint.

Usage from host::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh <s3cmd> ...


For example, this creates an S3 bucket named ``dev_bucket``::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh mb s3://dev_bucket/


This copies the contents of ``./testdata`` into the ``dev_bucket``::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh sync ./testdata s3://dev_bucket/


This lists the contents of the bucket::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh ls s3://dev_bucket/


Since this is just a wrapper, you can get help::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh help


``scripts/add_crashid_to_queue.py``
-----------------------------------

This script adds crash ids to the specified queue. Typically, you want to add
crash ids to the ``socorro.normal`` queue, but if you're testing priority
processing you'd use ``socorro.priority``.

Usage from host::

  $ docker-compose run processor scripts/add_crashid_to_queue.py <queue> <crashid> [<crashid> ...]


.. Note::

   You can run this script with ``docker/as_me.sh``, too. It's adding items to a
   queue, so it doesn't touch your file system and thus it doesn't matter what
   uid/gid it runs under.


For example::

  $ docker-compose run processor scripts/add_crashid_to_queue.py socorro.normal 5c9cecba-75dc-435f-b9d0-289a50170818


.. Note::

   Processing will fail unless the crash data is in the S3 container first!


.. Warning::

   August 17th, 2017: Everything below this point is outdated.


Troubleshooting
===============

journalctl is a good place to look for Socorro logs, especially if services
are not starting up or are crashing.

Socorro supports syslog and raven for application-level logging of all
services (including web services).
