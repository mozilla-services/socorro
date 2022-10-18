minidump-stackwalk
==================

Socorro uses ``stackwalker`` from
`<https://github.com/rust-minidump/rust-minidump>`__.


releases
--------

We have a repository with scripts for maintaining the version we use in
Socorro. We also tag, compile, and release binaries for Socorro builds.
`<https://github.com/mozilla-services/socorro-stackwalk>`__.

There are instructions in the ``README.md`` for maintaining it.


debugging
---------

In the ``socorro`` repository, there's a ``bin/run_mdsw.sh`` script for running
``stackwalker`` on minidumps like the processor does.

There are also scripts in ``socorro-stackwalk`` repository for debugging
stackwalk issues.
