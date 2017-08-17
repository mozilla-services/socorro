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


.. Warning::

   August 17th, 2017: Everything below this point is outdated.


Troubleshooting
===============

journalctl is a good place to look for Socorro logs, especially if services
are not starting up or are crashing.

Socorro supports syslog and raven for application-level logging of all
services (including web services).
