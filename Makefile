# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

.PHONY: clean

clean:
	-rm .docker-build
	-rm -rf build breakpad stackwalk google-breakpad breakpad.tar.gz
	cd minidump-stackwalk && make clean

.PHONY: dockerbuild dockersetup lint dockertest dockertestshell dockerrun

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
	${DC} run webapp /app/docker/run_setup.sh

lint: my.env
	${DC} run processor flake8

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
