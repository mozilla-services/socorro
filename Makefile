# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

.PHONY: clean default docs help lint

# Include my.env and export it so variables set in there are available
# in the Makefile.
include my.env
export

# Set these in the environment to override them. This is helpful for
# development if you have file ownership problems because the user
# in the container doesn't match the user on your host.
SOCORRO_UID ?= 10001
SOCORRO_GID ?= 10001

default:
	@echo "You need to specify a subcommand. See \"make help\" for options."
	@exit 1

help:
	@echo "Socorro make rules:"
	@echo ""
	@echo "  build            - build docker containers"
	@echo "  run              - docker-compose up the entire system for dev"
	@echo ""
	@echo "  shell            - open a shell in the base container"
	@echo "  clean            - remove all build, test, coverage and Python artifacts"
	@echo "  lint             - check style with flake8"
	@echo "  test             - run unit tests"
	@echo "  testshell        - open a shell for running tests"
	@echo "  docs             - generate Sphinx HTML documentation, including API docs"
	@echo ""
	@echo "  setup            - set up Postgres, Elasticsearch, and local S3"
	@echo "  updatedata       - add/update necessary database data"
	@echo ""
	@echo "See https://socorro.readthedocs.io/ for more documentation."

clean:
	-rm .docker-build
	-rm -rf build breakpad stackwalk google-breakpad breakpad.tar.gz
	-rm -rf .cache
	cd minidump-stackwalk && make clean

docs: my.env
	${DC} run docs ./docker/run_build_docs.sh

lint: my.env
	${DC} run webapp ./docker/run_lint.sh

.PHONY: build setup test testshell run dependencycheck stop

DC := $(shell which docker-compose)

my.env:
	@if [ ! -f my.env ]; \
	then \
	echo "Copying my.env.dist to my.env..."; \
	cp docker/config/my.env.dist my.env; \
	fi

.docker-build:
	make build

build: my.env
	${DC} build --build-arg userid=${SOCORRO_UID} --build-arg groupid=${SOCORRO_GID} base
	${DC} build webapp  # crontabber is based off of the webapp image
	${DC} build processor crontabber docs oidcprovider
	touch .docker-build

# NOTE(willkg): We run setup in the webapp container because the webapp will own
# postgres going forward and has the needed environment variables.
setup: my.env .docker-build
	${DC} run webapp /app/docker/run_setup.sh

test: my.env .docker-build
	./docker/run_tests_in_docker.sh ${ARGS}

testshell: my.env .docker-build
	./docker/run_tests_in_docker.sh --shell

updatedata: my.env
	./docker/run_update_data.sh

run: my.env
	${DC} up webapp processor webpack

stop: my.env
	${DC} stop

dependencycheck: my.env
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

# FIXME(willkg): We deprecated these make rules in favor of ones without
# the "docker" prefix. Remove these after August 2018.
.PHONY: dockerbuild dockertest dockertestshell dockerrun dockersetup dockerupdatedata

dockerbuild:
	$(error DEPRECATED: use "make build" instead)

dockertest:
	$(error DEPRECATED: use "make test" instead)

dockertestshell:
	$(error DEPRECATED: use "make testshell" instead)

dockerrun:
	$(error DEPRECATED: use "make run" instead)

dockersetup:
	$(error DEPRECATED: use "make setup" instead)

dockerupdatedata:
	$(error DEPRECATED: use "make updatedata" instead)
