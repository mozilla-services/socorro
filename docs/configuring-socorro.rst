.. index:: configuring-socorro

Configure and run Socorro
=========================

Storing configuration in Consul
-------------------------------

Socorro uses a distributed configuration service called Consul to hold
configuration - https://consul.io/intro/getting-started/install.html

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

Below is the minimum viable configuration to get collection and
processing working on a single node via Consul's REST interface::

    curl -s -X PUT -d "socorro.webapi.servers.WSGIServer" localhost:8500/v1/kv/socorro/collector/web_server.wsgi_server_class
    curl -s -X PUT -d "/path/to/your/symbols" localhost:8500/v1/kv/socorro/processor/processor.raw_to_processed_transform.BreakpadStackwalkerRule.processor_symbols_pathname_list

Note that Consul also has a Web UI you can use to get/set keys if you prefer.

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
by submitting a breakpad minidump. If you don't have one, you can download a test one from https://github.com/mozilla/socorro/blob/master/testcrash/raw/7d381dc5-51e2-4887-956b-1ae9c2130109.dump and submit it with curl::

  curl -F 'ProductName=Test' \
       -F 'Version=1.0' \
       -F upload_file_minidump=@7d381dc5-51e2-4887-956b-1ae9c2130109.dump \
       http://crash-reports/submit

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

Then, configure Socorro Processor to use Elasticsearch::

  curl -s -X PUT -d "socorro.external.es.crashstorage.ESCrashStorage" localhost:8500/v1/kv/socorro/processor/destination.crashstorage_class
  curl -s -X PUT -d "localhost" localhost:8500/v1/kv/socorro/common/resource.elasticsearch.elasticSearchHostname

No need to restart socorro-processor, envconsul will take care of this.

Now processed crashes will also be written to Elasticsearch.

You can download the latest version of Kibana from 
https://www.elastic.co/products/kibana and use it to explore the data.

Distributed Socorro
-------------------

You can see an example of how Mozilla configures a fully distributed Socorro
in AWS using Consul at https://github.com/mozilla/socorro-infra/

Socorro has a very powerful and expressive configuration system, and can
be configured to read from and write to a number of different data stores 
(S3, Elasticsearch, HBase, PostgreSQL) and use queues (RabbitMQ)

For instance, to have processor store crashes to both to the filesystem and to
ElasticSearch::

  curl -s -X PUT -d "socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage, socorro.external.es.crashstorage.ESCrashStorage, socorro.external.boto.crashstorage.BotoS3CrashStorage" localhost:8500/v1/kv/socorro/processor/destination.storage_classes
  curl -s -X PUT -d "socorro.external.crashstorage_base.PolyCrashStorage" localhost/v1/kv/socorro/processor/destination.crashstorage_class
  curl -s -X PUT -d "socorro.external.fs.crashstorage.FSTemporaryStorage" localhost:8500/v1/kv/socorro/processor/storage.crashstorage0_class=socorro.external.fs.crashstorage.FSTemporaryStorage
  curl -s -X PUT -d "socorro.external.es.crashstorage.ESCrashStorage" localhost:8500/v1/kv/socorro/processor/destination.storage1.crashstorage_class

AWS Simple Storage Service (S3)
-------------------------------

Socorro supports Amazon S3 (or compatible, like Ceph), for instance to add
support for Processor to put both unprocessed and processed crashes into S3::

  curl -s -X PUT -d "socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage, socorro.external.es.crashstorage.ESCrashStorage, socorro.external.boto.crashstorage.BotoS3CrashStorage" localhost:8500/v1/kv/socorro/processor/destination.storage_classes
  curl -s -X PUT -d "socorro.external.boto.crashstorage.BotoS3CrashStorage" localhost:8500/v1/kv/socorro/processor/destination.storage2.crashstorage_class

Crash-stats and PostgreSQL
--------------------------

Mozilla runs a service at https://crash-stats.mozilla.org that produces
graphs and reports for developers.

Both the crash-stats app and the PostgreSQL schema it depends on are very
Mozilla-specific and contains a lot of features that aren't generally useful,
like support for Mozilla's release model and a way of redacting private info
so crashes can be exposed to the public.

You probably do not want to install this:
:ref:`configuring-crashstats-chapter`
