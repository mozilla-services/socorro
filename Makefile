# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

.PHONY: all test bootstrap install lint clean breakpad json_enhancements_pg_extension package

all: test

test: bootstrap
	./scripts/test.sh

dev:
	SOCORRO_DEVELOPMENT_ENV=1 ./scripts/bootstrap.sh

bootstrap:
	./scripts/bootstrap.sh

install: bootstrap
	./scripts/install.sh

package: install
	./scripts/package.sh

lint:
	./scripts/lint.sh

clean:
	./scripts/clean.sh

breakpad:
	PREFIX=`pwd`/stackwalk/ SKIP_TAR=1 ./scripts/build-breakpad.sh

json_enhancements_pg_extension: bootstrap
	./scripts/json-enhancements.sh


# Docker related rules

.PHONY: dockerbuild dockershell dockerclean

DC := $(shell which docker-compose)

.docker-build:
	make dockerbuild

dockerbuild:
	${DC} build base
	${DC} build processor
	touch .docker-build

dockershell: .docker-build
	${DC} run --service-ports --entrypoint bash base

# NOTE(willkg): We run setup in the webapp container because the webapp will own
# postgres going forward and has the needed environment variables.
# FIXME(willkg): These are not idempotent, but they should be. Plus we should
# run migrations here, too.
dockersetup: .docker-build
	-${DC} run --entrypoint /app/docker/run_setup_postgres.sh webapp
	-${DC} run --entrypoint /app/docker/run_setup_elasticsearch.sh webapp

dockerclean:
	rm .docker-build

dockertest:
	${DC} run test /app/docker/run_test.sh

dockerrun:
	${DC} up webapp processor
