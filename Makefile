# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

ABS_PREFIX = $(shell readlink -f $(PREFIX))
VIRTUALENV=$(CURDIR)/socorro-virtualenv

PG_RESOURCES = $(if $(database_hostname), resource.postgresql.database_hostname=$(database_hostname)) $(if $(database_username), secrets.postgresql.database_username=$(database_username)) $(if $(database_password), secrets.postgresql.database_password=$(database_password)) $(if $(database_port), resource.postgresql.database_port=$(database_port)) $(if $(database_name), resource.postgresql.database_name=$(database_name))
RMQ_RESOURCES = $(if $(rmq_host), resource.rabbitmq.host=$(rmq_host)) $(if $(rmq_virtual_host), resource.rabbitmq.virtual_host=$(rmq_virtual_host)) $(if $(rmq_user), secrets.rabbitmq.rabbitmq_user=$(rmq_user)) $(if $(rmq_password), secrets.rabbitmq.rabbitmq_password=$(rmq_password))
ES_RESOURCES = $(if $(elasticsearch_urls), resource.elasticsearch.elasticsearch_urls=$(elasticsearch_urls)) $(if $(elasticSearchHostname), resource.elasticsearch.elasticSearchHostname=$(elasticSearchHostname)) $(if $(elasticsearch_index), resource.elasticsearch.elasticsearch_index=$(elasticsearch_index))

.PHONY: all test bootstrap install lint clean breakpad stackwalker json_enhancements_pg_extension

all: test

test: bootstrap
	bash ./scripts/test.sh

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
	bash ./scripts/json-enhancements.sh

stackwalker:
	# Build JSON stackwalker
	# Depends on breakpad, run "make breakpad" if you don't have it yet
	cd minidump-stackwalk; make
	cp minidump-stackwalk/stackwalker stackwalk/bin
