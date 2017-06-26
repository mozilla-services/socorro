.. _deploying-socorro-chapter:

=================
Deploying Socorro
=================

This chapter covers running Socorro in a server environment.

FIXME(willkg): Write this.


A note about support
====================

This is a very Mozilla-specific product. We do not currently have the capacity
to support external users. If you are looking to use Socorro for your product,
maybe you want to consider alternatives like `electron/mini-breakpad-server
<https://github.com/electron/mini-breakpad-server>`_.


Where'd the collector go? (April 2017)
--------------------------------------

In April 2017, we spun off the collector as a separate project called Antenna.
Antenna has a reduced project scope and works differently than the collector did
in some ways. You can find it at
`<https://github.com/mozilla-services/antenna>`_.

After getting that working, we removed the collector code from the Socorro
repository. We're removing other code, too.

If you rely on that collector, the last good release is `270
<https://github.com/mozilla/socorro/releases/tag/270>`_.

You can get it with something like this::

    git clone https://github.com/mozilla/socorro
    git checkout 270


 Or get the tarball::

    wget https://github.com/mozilla/socorro/archive/270.tar.gz
