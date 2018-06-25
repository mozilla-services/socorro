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

To use::

    $ socorro-cmd signature CRASHID [CRASHID ...]


Pulling crash ids from the file ``crashids.txt``::

    $ cat crashids.txt | socorro-cmd signature


Pulling crash ids from another script::

    $ ./scripts/fetch_crashids.py --num=10 | socorro-cmd signature


Spitting output in CSV format to more easily analyze results for generating
signatures for multiple crashes::

    $ cat crashids.txt | socorro-cmd signature --format=csv


For more argument help, see::

    $ socorro-cmd signature --help


.. Note::

   You need to run this inside a Socorro environment. For example, you could
   do this::

     $ docker-compose run processor bash
     app@.../app$ socorro-cmd signature --help


library
-------

This code can sort of be used as a library. It's been decoupled from many of
Socorro's bits, but still has some requirements. Roughtly, it requires:

* requests
* socorro.siglists
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
