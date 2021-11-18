minidump-stackwalk
==================

Socorro uses ``stackwalker`` from
`<https://github.com/mozilla-services/minidump-stackwalk>`_.

There's a ``bin/run_mdsw.sh`` script for running ``stackwalker`` on
minidumps to test it out.

See the minidump-stackwalk repo for more details.


.. Note::

   Update: November 18th, 2021

   We're in the process of switching to `rust-minidump minidump-stackwalk
   <https://github.com/luser/rust-minidump>`_.

   If you have any bugs with stackwalking, symbolication, etc--write up issues
   there.
