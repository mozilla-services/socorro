Socorro
=======

Socorro is a set of components for collecting, processing and reporting on crashes. It is used by Mozilla for tracking crashes of Firefox, B2G, Thunderbird and other projects. The production Mozilla install is public and hosted at https://crash-stats.mozilla.com/

The components which make up Socorro are:

* Collector - collects breakpad minidump crashes which come in over HTTP POST
* Processor - turn breakpad minidump crashes into stack traces and other info
* Middleware - provide HTTP REST interface for JSON reports and real-time data
* Web UI aka crash-stats - django-based web app for visualizing crash data

Socorro is available as an RPM for RHEL/CentOS, or you can build from source
on Mac OSX, Ubuntu or RHEL/CentOS.

* For production installation, proceed to :ref:`production_install-chapter`.
* If you want to build from source, see the :ref:`development-chapter` section.

We welcome contributions!

* Start here to contribute to documentation: :ref:`writingdocs-chapter`.
* Start here to contribute code: :ref:`newdeveloperguide-chapter`.

See http://wiki.mozilla.org/Breakpad for up-to-date information about development team activity and our meetings.

This documentation is `available on readthedocs <https://socorro.readthedocs.io>`_. The source and current development activity is `available on Github <https://github.com/mozilla/socorro/>`_.

The Socorro development mailing list is https://lists.mozilla.org/listinfo/tools-socorro


Support
=======

This is a very Mozilla-specific product. We do not currently have the capacity
to support external users. If you are looking to use Socorro for your product,
maybe you want to consider alternatives like `electron/mini-breakpad-server
<https://github.com/electron/mini-breakpad-server>`_.


May 3rd, 2017 Update
--------------------

For the last year or so, we've been removing code and making changes that aren't
backwards compatible. A couple of weeks ago, we (Mozilla) extracted the
collector out of Socorro into a separate repository. Because of that, we're
going to start removing code.

If you rely on that collector, the last good commit sha is `55beaf1
<https://github.com/mozilla/socorro/commit/55beaf1281e7b522e0526b2aa2bf74d15f6c1263>`_.

You can get it with something like this::

    git clone https://github.com/mozilla/socorro
    git checkout 55beaf1


 Or get the tarball::

    wget https://github.com/mozilla/socorro/archive/55beaf1.tar.gz


Contents
========

.. toctree::
   :numbered:
   :hidden:

   production-install
   configuring-socorro
   symbols
   troubleshoot
   development/index
