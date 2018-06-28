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

You need to run this inside a Socorro environment. For example, you could
run this in the processor Docker container. You can start a container
like that like this::

    $ docker-compose run processor bash


Once you're in your Socorro environment, you can run signature generation.
You can pass it crash ids via the command line as arguments::

    socorro-cmd signature CRASHID [CRASHID...]


It can also take crash ids from stdin.

Some examples:

* pulling crash ids from the file ``crashids.txt``::

    $ cat crashids.txt | socorro-cmd signature

* pulling crash ids from another script::

    $ socorro-cmd fetch_crashids --num=10 | socorro-cmd signature

* spitting output in CSV format to more easily analyze results for generating
  signatures for multiple crashes::

    $ cat crashids.txt | socorro-cmd signature --format=csv


For more argument help, see::

    $ socorro-cmd signature --help


library
-------

This code can sort of be used as a library. It's been decoupled from many of
Socorro's bits, but still has some requirements. Roughtly, it requires:

* requests
* ujson


The main class is ``socorro.signature.SignatureGenerator``. It takes a pipeline
of rules to use to generate signatures.

Rough usage::

    from socorro.signature import SignatureGenerator

    generator = SignatureGenerator()

    raw_crash = get_raw_crash_from_somewhere()
    processed_crash = get_processed_crash_from_somewhere()

    ret = generator.generate(raw_crash, processed_crash)
    print(ret['signature'])


.. Note::

   If you're interested in using this library, write up a bug and let us know
   the use case and we'll work with you to make it more library-friendly to meet
   your needs.
