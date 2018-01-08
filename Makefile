# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

.PHONY: package

# Used by infra to build rpm
package:
	./scripts/bootstrap.sh
	./scripts/install.sh
	./scripts/package.sh

# Docker related rules

.PHONY: dockerbuild dockersetup dockerclean dockertest dockertestshell dockerrun

DC := $(shell which docker-compose)

my.env:
	@if [ ! -f my.env ]; \
	then \
	echo "Copying my.env.dist to my.env..."; \
	cp docker/config/my.env.dist my.env; \
	fi

.docker-build:
	make dockerbuild

dockerbuild: my.env
	${DC} build base
	${DC} build webapp # crontabber is based off of the webapp image
	${DC} build processor crontabber docs
	touch .docker-build

# NOTE(willkg): We run setup in the webapp container because the webapp will own
# postgres going forward and has the needed environment variables.
dockersetup: my.env .docker-build
	${DC} run webapp /app/docker/run_setup_postgres.sh
	${DC} run processor /app/docker/run_recreate_s3_buckets.sh
	${DC} run processor /app/scripts/socorro clear_es_indices

dockerclean:
	rm .docker-build

dockertest: my.env
	./docker/run_tests_in_docker.sh ${ARGS}

dockertestshell: my.env
	./docker/run_tests_in_docker.sh --shell

dockerdocs: my.env
	./docker/as_me.sh --container docs ./docker/run_build_docs.sh

dockerupdatedata: my.env
	./docker/run_update_data.sh

dockerrun: my.env
	${DC} up webapp processor

dockerstop: my.env
	${DC} stop

dockerdependencycheck: my.env
	${DC} run crontabber ./docker/run_dependency_checks.sh
