=======
Socorro
=======

Socorro is a Mozilla-centric set of services for collecting, processing, and
displaying crash reports from clients using the `Breakpad libraries
<http://code.google.com/p/google-breakpad/>`_.


Support
=======

This is a very Mozilla-specific product. We do not currently have the capacity
to support external users.

If you are looking to use Socorro for your product, maybe you want to consider
alternatives:

* `electron/mini-breakpad-server <https://github.com/electron/mini-breakpad-server>`_
* `wk8/sentry_breakpad <https://github.com/wk8/sentry_breakpad>`_


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


Installation
============

Documentation about installing Socorro is available on ReadTheDocs:
`<https://socorro.readthedocs.io/en/latest>`_


Releases
========

We use continuous development, so we release quite often. See our list of releases:

https://github.com/mozilla/socorro/releases


Communication
=============

We have a mailing list for Socorro users that you can join here:
https://lists.mozilla.org/listinfo/tools-socorro

Please help each other.

Devs hang out in the Socorro/Breakpad IRC channel:
`<irc://irc.mozilla.org/breakpad>`_


Development
===========

Current deployment status: https://whatsdeployed.io/s-7M7

Mozilla-centric Infrastructure (AWS) code: https://github.com/mozilla/socorro-infra
