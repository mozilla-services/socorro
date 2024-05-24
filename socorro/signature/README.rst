.. _signaturegeneration-chapter-module:

Signature generation module
===========================

This Python module covers crash signature generation.


command line interface
----------------------

This module defines a command line interface for signature generation. Given a
crash id, it pulls the raw and processed data from Socorro -prod, generates a
signature using the code in this module, and then tells you the original
signature and the newly generated one.

This can be used for testing signature generation changes, regression testing,
and astounding your friends at parties.

You need to run this inside a Socorro environment. For example, you could run
this in the processor Docker container. You can start a container like that
like this::

    $ make shell


Once you're in your Socorro environment, you can run signature generation. You
can pass it crash ids via the command line as arguments::

    socorro-cmd signature CRASHID [CRASHID...]


It can also take crash ids from stdin.

Examples:

* getting crash ids from the file ``crashids.txt``::

    $ cat crashids.txt | socorro-cmd signature

* getting crash ids from another command::

    $ socorro-cmd fetch_crashids --num=10 | socorro-cmd signature

  .. Note::

     ``fetch_crashids`` defaults to Firefox. If you want a different product, use the ``--product`` argument.
     See ``socorro-cmd fetch_crashids --help`` for options.

* getting crash ids for crash reports with a specific signature and then
  checking to see if the signatures have changed::

    $ socorro-cmd fetch_crashids --signature='js::NativeGetProperty' --num=5 | socorro-cmd signature

* spitting output in CSV format to more easily analyze results for generating
  signatures for multiple crashes::

    $ cat crashids.txt | socorro-cmd signature --format=csv


For more argument help, see::

    $ socorro-cmd signature --help


library
-------

This code is also available as library that's updated periodically by WillKG.

If you're interested in using it, let us know.

:PyPI: https://pypi.org/project/siggen/
:GitHub: https://github.com/willkg/socorro-siggen/
