# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

ABS_PREFIX = $(shell readlink -f $(PREFIX))
VIRTUALENV=$(CURDIR)/socorro-virtualenv
PYTHONPATH = "."
NOSE = $(VIRTUALENV)/bin/nosetests socorro -s
SETUPDB = $(VIRTUALENV)/bin/python ./socorro/external/postgresql/setupdb_app.py
JENKINS_CONF = jenkins.py.dist
ENV = env

PG_RESOURCES = $(if $(database_hostname), resource.postgresql.database_hostname=$(database_hostname)) $(if $(database_username), secrets.postgresql.database_username=$(database_username)) $(if $(database_password), secrets.postgresql.database_password=$(database_password)) $(if $(database_port), resource.postgresql.database_port=$(database_port)) $(if $(database_name), resource.postgresql.database_name=$(database_name))
RMQ_RESOURCES = $(if $(rmq_host), resource.rabbitmq.host=$(rmq_host)) $(if $(rmq_virtual_host), resource.rabbitmq.virtual_host=$(rmq_virtual_host)) $(if $(rmq_user), secrets.rabbitmq.rabbitmq_user=$(rmq_user)) $(if $(rmq_password), secrets.rabbitmq.rabbitmq_password=$(rmq_password))
ES_RESOURCES = $(if $(elasticsearch_urls), resource.elasticsearch.elasticsearch_urls=$(elasticsearch_urls)) $(if $(elasticSearchHostname), resource.elasticsearch.elasticSearchHostname=$(elasticSearchHostname)) $(if $(elasticsearch_index), resource.elasticsearch.elasticsearch_index=$(elasticsearch_index))

.PHONY: all test bootstrap install lint clean breakpad stackwalker json_enhancements_pg_extension

all: test

test: bootstrap
	# jenkins only settings for the pre-configman components
	# can be removed when all tests are updated to use configman
	if [ $(WORKSPACE) ]; then cd socorro/unittest/config; cp $(JENKINS_CONF) commonconfig.py; fi;
	# setup any unset test configs and databases without overwriting existing files
	cd config; for file in *.ini-dist; do if [ ! -f `basename $$file -dist` ]; then cp $$file `basename $$file -dist`; fi; done
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_integration_test --database_username=$(database_username) --database_hostname=$(database_hostname) --database_password=$(database_password) --database_port=$(database_port) --database_superusername=$(database_superusername) --database_superuserpassword=$(database_superuserpassword) --dropdb --logging.stderr_error_logging_level=40 --unlogged
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_test --database_username=$(database_username) --database_hostname=$(database_hostname) --database_password=$(database_password) --database_port=$(database_port) --database_superusername=$(database_superusername) --database_superuserpassword=$(database_superuserpassword) --dropdb --no_schema --logging.stderr_error_logging_level=40 --unlogged
	cd socorro/unittest/config; for file in *.py.dist; do if [ ! -f `basename $$file .dist` ]; then cp $$file `basename $$file .dist`; fi; done
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_migration_test --database_username=$(database_username) --database_hostname=$(database_hostname) --database_password=$(database_password) --database_port=$(database_port) --database_superusername=$(database_superusername) --database_superuserpassword=$(database_superuserpassword) --dropdb --logging.stderr_error_logging_level=40 --unlogged
	PYTHONPATH=$(PYTHONPATH) $(VIRTUALENV)/bin/alembic -c config/alembic.ini downgrade -1
	PYTHONPATH=$(PYTHONPATH) $(VIRTUALENV)/bin/alembic -c config/alembic.ini upgrade +1
	# run tests
	$(ENV) $(PG_RESOURCES) $(RMQ_RESOURCES) $(ES_RESOURCES) PYTHONPATH=$(PYTHONPATH) $(NOSE)
	# test webapp
	cd webapp-django; ./bin/jenkins.sh

bootstrap:
	bash ./scripts/bootstrap.sh

install: bootstrap
	bash ./scripts/install.sh

lint:
	bash ./scripts/lint.sh

clean:
	bash ./scripts/clean.sh

breakpad:
	PREFIX=`pwd`/stackwalk/ SKIP_TAR=1 ./scripts/build-breakpad.sh

json_enhancements_pg_extension: bootstrap
    # This is only run manually, as it is a one-time operation
    # to be performed at system installation time, rather than
    # every time Socorro is built
	if [ ! -f `pg_config --pkglibdir`/json_enhancements.so ]; then sudo env PATH=$$PATH $(VIRTUALENV)/bin/python -c "from pgxnclient import cli; cli.main(['install', 'json_enhancements'])"; fi

stackwalker:
	# Build JSON stackwalker
	# Depends on breakpad, run "make breakpad" if you don't have it yet
	cd minidump-stackwalk; make
	cp minidump-stackwalk/stackwalker stackwalk/bin
