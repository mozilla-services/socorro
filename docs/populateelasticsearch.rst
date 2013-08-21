.. index:: populateelasticsearch

.. _populateelasticsearch-chapter:

Populate ElasticSearch
======================

Install ElasticSearch
---------------------

First you need to install ElasticSearch. The procedure is well described in
this tutorial: `Setting up elasticsearch`_. Don't bother configuring ES if
you don't know you will need it, it generally works just fine out of the box.

.. _`Setting up elasticsearch`: http://www.elasticsearch.org/tutorials/2010/07/01/setting-up-elasticsearch.html

`Note: ElasticSearch is not yet included in our Vagrant dev VMs but should
be sometime soon.`

Increase open files limit
-------------------------

ElasticSearch needs to open a lot of files when indexing, often reaching
the limits imposed by UNIX systems. To avoid errors when indexing, you will
have to increase the limits imposed by your OS.

First see what user is running ElasticSearch. It may be root or vagrant. Use
``top`` for example and look for an ``elasticsearch-l`` process. Then edit
``/etc/security/limits.conf`` and add at the end the following::

    root soft nofile 4096
    root hard nofile 10240

Replace ``root`` with ``vagrant`` (or whatever user is running ES) if needed,
save and restart your VM.

You will also need to increase the system-wide file descriptors limit by
editing ``/etc/sysctl.conf`` and adding at the end::

    fs.file-max = 100000

After you saved and closed the file, run ``sysctl -p``, then
``cat /proc/sys/fs/file-max`` to verify it worked. No restart is required here.

`Note: I am not sure whether restarting the VM is necessary, or if ElasticSearch
only is needed. Don't hesitate to make this more precise with the result
of your experiments.`

`Source:` http://www.cyberciti.biz/faq/linux-increase-the-maximum-number-of-open-files/

Download the dump
-----------------

You can get a recent dump for ElasticSearch in
http://people.mozilla.org/~agaudebert/socorro/es-dumps/.

You will also need to get the mapping of our Socorro indexes:
http://people.mozilla.org/~agaudebert/socorro/es-dumps/mapping.json

Run the script
--------------

The script to import crashes into ElasticSearch is not yet merged into our
official repository. To get it, you will need to fetch
``github.com/AdrianGaudebert/socorro`` and checkout branch
``696722-script-import-es``::

    git remote add AdrianGaudebert https://github.com/AdrianGaudebert/socorro.git
    git fetch AdrianGaudebert
    git branch --track 696722-script-import-es AdrianGaudebert/696722-script-import-es
    git checkout 696722-script-import-es

Before you can run the script, you will have to stop supervisord::

    sudo /etc/init.d/supervisor force-stop

The script is called ``movecrashes.py`` and is in ``.../scripts/``. It has a
few dependencies over Socorro and thus needs to be ran from the root of a
Socorro directory with ``$PYTHONPATH = .``. Use it as follow::

    python scripts/movecrashers.py import /path/to/dump.tar /path/to/mapping.json

This will simply import all crash reports contained in the dump into
ElasticSearch, without cleaning anything before. If you want to have more data
than available in the dump, you can just run that ``import`` again and
create duplicates.

If you want to clean the old socorro data first, just run ``rebuild`` instead
of ``import``::

    python scripts/movecrashers.py rebuild /path/to/dump.tar /path/to/mapping.json

Note that this will only delete indexes called ``socorro_xxxxxx``. If you're
using a shared ES instance, or have other indexes you want to keep, there is
no risk they get deleted in this process.
