# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

.PHONY: clean default docs help lint

default:
	@echo "You need to specify a subcommand. See \"make help\" for options."
	@exit 1

help:
	@echo "Socorro make rules:"
	@echo ""
	@echo "  dockerbuild      - build docker containers for dev"
	@echo "  dockerrun        - docker-compose up the entire system for dev"
	@echo ""
	@echo "  shell            - open a shell in the base container"
	@echo "  clean            - remove all build, test, coverage and Python artifacts"
	@echo "  lint             - check style with flake8"
	@echo "  dockertest       - run unit tests"
	@echo "  dockertestshell  - open a shell in the systemtest container"
	@echo "  docs             - generate Sphinx HTML documentation, including API docs"
	@echo ""
	@echo "  dockersetup      - set up Postgres, Elasticsearch, and local S3"
	@echo "  dockerupdatedata - add/update necessary database data"
	@echo ""
	@echo "See https://socorro.readthedocs.io/ for more documentation."

clean:
	-rm .docker-build
	-rm -rf build breakpad stackwalk google-breakpad breakpad.tar.gz
	cd minidump-stackwalk && make clean

docs: my.env
	./docker/as_me.sh --container docs ./docker/run_build_docs.sh

lint: my.env
	${DC} run processor flake8

.PHONY: dockerbuild dockersetup dockertest dockertestshell dockerrun

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

dockerlint: my.env .docker-build
	./docker/run_lints_in_docker.sh ${ARGS}

dockertest: my.env .docker-build
	./docker/run_tests_in_docker.sh ${ARGS}

dockertestshell: my.env .docker-build
	./docker/run_tests_in_docker.sh --shell

dockerupdatedata: my.env
	./docker/run_update_data.sh

dockerrun: my.env
	${DC} up webapp processor

dockerstop: my.env
	${DC} stop

dockerdependencycheck: my.env
	${DC} run crontabber ./docker/run_dependency_checks.sh

# Python 3 transition related things

.PHONY: dockerbuild3 dockertest3 dockertestshell3

.docker-build3:
	make dockerbuild3

dockerbuild3: my.env
	${DC} build testpython3
	touch .docker-build3

dockertest3: my.env .docker-build3
	USEPYTHON=3 ./docker/run_tests_in_docker.sh ${ARGS}

dockertestshell3: my.env .docker-build3
	USEPYTHON=3 ./docker/run_tests_in_docker.sh --shell
