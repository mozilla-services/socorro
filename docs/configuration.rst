=============
Configuration
=============

.. contents::
   :local:

Processor configuration
=======================

Honcho runs a processor process and a disk cache manager process. Both share
the same configuration.

.. automoduleconfig:: socorro.mozilla_settings._config
   :show-table:
   :hide-name:
   :case: upper


Webapp / crontabber configuration
=================================

Gunicorn configuration:

.. everett:option:: GUNICORN_TIMEOUT
   :default: "300"

   Specifies the timeout value in seconds.

   https://docs.gunicorn.org/en/stable/settings.html#timeout

   Used in `bin/run_webapp.sh
   <https://github.com/mozilla-services/socorro/blob/main/bin/run_webapp.sh>`_.


.. everett:option:: GUNICORN_WORKERS
   :default: "1"

   Specifies the number of gunicorn workers.

   You should set it to ``(2 x $num_cores) + 1``.

   https://docs.gunicorn.org/en/stable/settings.html#workers

   http://docs.gunicorn.org/en/stable/design.html#how-many-workers

   Used in `bin/run_webapp.sh
   <https://github.com/mozilla-services/socorro/blob/main/bin/run_webapp.sh>`_.


.. everett:option:: GUNICORN_WORKER_CLASS
   :default: "sync"

   Specifies the gunicorn worker type.

   https://docs.gunicorn.org/en/stable/settings.html#workers

   Used in `bin/run_webapp.sh
   <https://github.com/mozilla-services/socorro/blob/main/bin/run_webapp.sh>`_.


.. everett:option:: GUNICORN_MAX_REQUESTS
   :default: "10000"

   The number of requests before recycling the gunicorn worker.

   https://docs.gunicorn.org/en/stable/settings.html#workers

   Used in `bin/run_webapp.sh
   <https://github.com/mozilla-services/socorro/blob/main/bin/run_webapp.sh>`_.


.. everett:option:: GUNICORN_MAX_REQUESTS_JITTER
   :default: "1000"

   The range to generate a random amount to add to max requests so that
   everything isn't restarting at the same time.

   https://docs.gunicorn.org/en/stable/settings.html#workers

   Used in `bin/run_webapp.sh
   <https://github.com/mozilla-services/socorro/blob/main/bin/run_webapp.sh>`_.


Webapp configuration:

.. automoduleconfig:: webapp.crashstats.settings.base._config
   :show-table:
   :hide-name:
   :case: upper
