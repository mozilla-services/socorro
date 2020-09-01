.. _processor-chapter:

=========
Processor
=========

The code for the processor is in ``socorro/processor/``.

Processor rules are in ``socorro/processor/rules/``.


Configuration
=============

Configuration for the processor is specified in environment variables.

FIXME(willkg): How to configure?


stackwalker
===========

The ``BreakpadStackwalkerRule2015`` processor rule runs a breakpad minidump
stackwalker on minidump files to extract information about the process. The
stackwalker is run as a subprocess.

Code and documentation for the stackwalker binares is in
`<https://github.com/mozilla-services/minidump-stackwalk/>`_.

The stackwalker binaries are added to the Docker image in ``/stackwalk``.

The stackwalker downloads breakpad SYM files from specified symbols server urls
to symbolicate stacks. Mozilla's crash ingestion pipeline points to the Mozilla
Symbols Server which holds symbols for all our product builds.

The stackwalker is set up to store temporary files it generates when
downloading SYM files in ``symbol_tmp_path`` and cache SYM files that have been
completely downloaded for a while in ``symbol_cache_path``. SYM files are big,
so you want to volume mount those paths into the Docker container.


Running in a local dev environment
==================================

To run the processor in the local dev environment, do::

  $ docker-compose up processor

That will bring up all the services the processor requires to run and start the
processor using the ``/app/docker/run_processor.sh`` script and the processor
configuration.

To use tools and also ease debugging in the container, you can run a shell::

  $ make shell

Then you can start and stop the processor and tweak files and all that jazz.


Running in a server environment
===============================

Add configuration to ``processor.env`` file.

Run the docker image using the ``processor`` command. Something like this::

    docker run \
        --env-file=processor.env \
        --volume /data:/data \
        mozilla/socorro_app processor

This runs the ``/app/docker/run_processor.sh`` script.
