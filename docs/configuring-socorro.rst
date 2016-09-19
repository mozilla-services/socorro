.. index:: configuring-socorro

Configure and run Socorro
=========================

Storing configuration in Consul
-------------------------------

Socorro apps get their configuration from environment variables. We suggest
using Consul to hold configuration:
https://consul.io/intro/getting-started/install.html

Consul must be running in order for Socorro apps to start up and access
their configuration. Normally you want to run a cluster (see the docs above)
but to start in a single node configuration add this to
/etc/consul/server.json::

  {
      "server": true,
      "bootstrap_expect": 1
  }

And restart Consul::

  sudo systemctl restart consul

The Socorro systemd service scripts use envconsul
(https://github.com/hashicorp/envconsul) to read the configuration from Consul
and set the environment.

To keep track of your configuration, it's recommended to make a "socorro-config"
directory and store these values there, and then load those into Consul as
a separate step.

Below is the minimum viable configuration to get collection working on a
single node:

.. code-block:: bash

    # Tell the Socorro app dispatcher which collector App to use
    application=socorro.collector.collector_app.CollectorApp

    # Run collector in WSGI mode, instead of the default dev server
    web_server__wsgi_server_class='socorro.webapi.servers.WSGIServer'

Put this into a file named "collector.conf" in your socorro-config folder.

Now, configure processor:

.. code-block:: bash

    new_crash_source__crashstorage_class='socorro.external.fs.crashstorage.FSDatedPermanentStorage'
    source__crashstorage_class='socorro.external.fs.crashstorage.FSPermanentStorage'
    new_crash_source__new_crash_source_class='socorro.external.fs.fs_new_crash_source.FSNewCrashSource'

Put this into a file named "processor.conf" in your socorro-config folder.

For processing to work, you must provide debug symbols from your build.
See http://code.google.com/p/google-breakpad/wiki/LinuxStarterGuide#Producing_symbols_for_your_application for more information.

You can put your symbols into `/home/socorro/symbols` which is the default,
or you can change this location if necessary:

.. code-block:: bash

    # This should be replaced with the path to your debug symbols.
    processor__raw_to_processed_transform__BreakpadStackwalkerRule__processor_symbols_pathname_list='@@@PATH_TO_YOUR_SYMBOLS@@@'

Make sure to change `@@@PATH_TO_YOUR_SYMBOLS@@@` to the real absolute path
to your symbols.

Put this into a file named "processor.conf" in your socorro-config folder.

Now load the contents of your socorro-config directory into Consul::

  cd ./socorro-config
  sudo setup-socorro.sh consul

Note that Consul also has a Web UI you can use to get/set keys if you prefer,
or you can use the REST interface directly. See the consul docs for more
information: https://consul.io

You can see that the keys are getting set in the environment correctly
by invoking envconsul::

  envconsul -prefix socorro env

Start services
--------------

These services start up uwsgi apps running under envconsul::

    sudo systemctl enable socorro-collector socorro-processor
    sudo systemctl start socorro-collector socorro-processor

Configure Nginx
---------------

Public-facing services like socorro-collector should be fronted by Nginx.

This is so we can run Socorro components under the
socorro user and not need to listen on privileged port 80, and also to
protect from slow clients. Nginx is also more efficient at handling static
assets.

You can find a working example config in
/etc/nginx/conf.d/socorro-collector.conf.sample
You should change server_name at minimum, the default is "crash-reports".

Copy the above .sample file to .conf and restart Nginx to activate::

  sudo systemctl restart nginx

Test collection and processing
------------------------------

Basic collection and processing should now be working. You can test this
by submitting a breakpad minidump. If you don't have one, you can download a test one from https://github.com/mozilla/socorro/blob/master/testcrash/raw/7d381dc5-51e2-4887-956b-1ae9c2130109.dump and submit it with curl.

Be sure to use the same server_name you configured in Nginx for socorro-collector:

.. code-block:: bash

  curl -H 'Host: crash-reports' \
       -F 'ProductName=Test' \
       -F 'Version=1.0' \
       -F upload_file_minidump=@7d381dc5-51e2-4887-956b-1ae9c2130109.dump \
       http://localhost/submit

If collection is working, you should be see a Crash ID returned::

  CrashID=bp-395cb5c2-f04e-4f54-b027-3df542150428

The above crash should be stored as .json/.dump files in ~socorro/crashes/ and
made available to the processor. Once processor runs you will see an additional
.jsonz file.

Both the collector and processor logs can be found in the systemd journal, use
the journalctl command to see them.

Graphs and reports using Elasticsearch and Kibana
-------------------------------------------------

Processor supports putting crashes into Elasticsearch.

First, run this to create the initial Elasticsearch indexes::

  sudo setup-socorro.sh elasticsearch

Then, configure Socorro Processor to use Elasticsearch:

.. code-block:: bash

  destination__crashstorage_class='socorro.external.es.crashstorage.ESCrashStorage'
  resource__elasticsearch__elasticsearch_index='socorro_reports'

Put this into the "processor.conf" in your socorro-config folder.

Next, set the Elasticsearch hostname:

.. code-block:: bash

   resource__elasticsearch__elasticSearchHostname='localhost'

Put this into the "common.conf" in your socorro-config folder. The
"socorro/common" prefix is shared with all the apps.

Now load the contents of your socorro-config directory into Consul::

  cd ./socorro-config
  sudo setup-socorro.sh consul

No need to restart socorro-processor, envconsul will take care of this.

Now processed crashes will also be written to Elasticsearch.

You can download the latest version of Kibana from
https://www.elastic.co/products/kibana and use it to explore the data.

Note - you will want to use the "socorro_reports" index, configured above,
and not the "socorro" one for Kibana.

Distributed Socorro
-------------------

You can see an example of how Mozilla configures a fully distributed Socorro
in AWS using Consul at https://github.com/mozilla/socorro-infra/

Socorro has a very powerful and expressive configuration system, and can
be configured to read from and write to a number of different data stores
(S3, Elasticsearch, PostgreSQL) and use queues (RabbitMQ)

For instance, to have processor store crashes to both to the filesystem and to
ElasticSearch:

.. code-block:: bash

  # Store the crash in multiple locations
  destination__crashstorage_class='socorro.external.crashstorage_base.PolyCrashStorage'
  # Specify crash storage types which will be used
  destination__storage_classes='socorro.external.fs.crashstorage.FSPermanentStorage, socorro.external.es.crashstorage.ESCrashStorage'
  # Store in the filesystem first (by default this is ~socorro/crashes/)
  destination__storage0__crashstorage_class='socorro.external.fs.crashstorage.FSPermanentStorage'
  # Store in Elasticsearch second
  destination__storage1__crashstorage_class='socorro.external.es.crashstorage.ESCrashStorage'

Put this into the "processor.conf" in your socorro-config folder.

Now load the contents of your socorro-config directory into Consul::

  cd ./socorro-config
  sudo setup-socorro.sh consul

AWS Simple Storage Service (S3)
-------------------------------

Socorro supports Amazon S3 (or compatible, like Ceph), for instance to add
support for Processor to put both unprocessed and processed crashes into S3:

.. code-block:: bash

  # Store the crash in multiple locations
  destination__crashstorage_class='socorro.external.crashstorage_base.PolyCrashStorage'
  # Specify crash storage types which will be used
  destination__storage_classes='socorro.external.boto.crashstorage.BotoS3CrashStorage, socorro.external.es.crashstorage.ESCrashStorage'
  # Store in S3 first
  destination__storage0__crashstorage_class='socorro.external.boto.crashstorage.BotoS3CrashStorage'
  # Store in Elasticsearch second
  destination__storage1__crashstorage_class='socorro.external.es.crashstorage.ESCrashStorage'

Put this into the "processor.conf" in your socorro-config folder.

Next, set the AWS bucket name, access key and secret access key:

.. code-block:: bash

  resource__boto__bucket_name='@@@BUCKET_NAME@@@'
  resource__boto__access_key='@@@ACCESS_KEY@@@'
  secrets__boto__secret_access_key='@@@SECRET_ACCESS_KEY@@@'

Put this into "common.conf" in your socorro-config directory.

Now load the contents of your socorro-config directory into Consul::

  cd ./socorro-config
  sudo setup-socorro.sh consul

Crash-stats and PostgreSQL
--------------------------

Mozilla runs a service at https://crash-stats.mozilla.org that produces
graphs and reports for developers.

Both the Crash-Stats app and the PostgreSQL schema it depends on are very
Mozilla-specific and contains a lot of features that aren't generally useful,
like support for Mozilla's release model and a way of redacting private info
so crashes can be exposed to the public.

You probably do not want to install this:
:ref:`configuring-crashstats-chapter`
