# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Include my.env and export it so variables set in there are available
# in the Makefile.
include my.env
export

# Set these in the environment to override them. This is helpful for
# development if you have file ownership problems because the user
# in the container doesn't match the user on your host.
SOCORRO_UID ?= 10001
SOCORRO_GID ?= 10001

DC := $(shell which docker-compose)


.PHONY: help
help: default

.PHONY: default
default:
	@echo "Usage: make RULE"
	@echo ""
	@echo "Socorro make rules:"
	@echo ""
	@echo "  build            - build docker containers"
	@echo "  run              - docker-compose up the entire system for dev"
	@echo "  stop             - stop all service containers"
	@echo ""
	@echo "  shell            - open a shell in the app container"
	@echo "  clean            - remove all build, test, coverage and Python artifacts"
	@echo "  lint             - check style with flake8"
	@echo "  test             - run unit tests"
	@echo "  testshell        - open a shell for running tests"
	@echo "  docs             - generate Sphinx HTML documentation, including API docs"
	@echo ""
	@echo "  setup            - set up Postgres, Elasticsearch, and local S3"
	@echo "  updatedata       - add/update necessary database data"
	@echo "  help             - see this text"
	@echo ""
	@echo "See https://socorro.readthedocs.io/ for more documentation."

.PHONY: clean
clean:
	-rm .docker-build*
	-rm -rf build breakpad stackwalk google-breakpad breakpad.tar.gz
	-rm -rf .cache
	cd minidump-stackwalk && make clean

.PHONY: docs
docs: my.env .docker-build-docs
	${DC} run docs ./docker/run_build_docs.sh

.PHONY: lint
lint: my.env
	${DC} run app shell ./docker/run_lint.sh

my.env:
	@if [ ! -f my.env ]; \
	then \
	echo "Copying my.env.dist to my.env..."; \
	cp docker/config/my.env.dist my.env; \
	fi

.docker-build:
	make build

.PHONY: build
build: my.env
	${DC} build --build-arg userid=${SOCORRO_UID} --build-arg groupid=${SOCORRO_GID} app
	${DC} build oidcprovider
	touch .docker-build

.docker-build-docs:
	make build-docs

.PHONY: build-docs
build-docs: my.env
	${DC} build docs
	touch .docker-build-docs

.PHONY: setup
setup: my.env .docker-build
	${DC} run app shell bash -c /app/docker/run_setup.sh

.PHONY: updatedata
updatedata: my.env
	./docker/run_update_data.sh

.PHONY: shell
shell: my.env .docker-build
	${DC} run app shell

.PHONY: test
test: my.env .docker-build
	./docker/run_tests_in_docker.sh ${ARGS}

.PHONY: testshell
testshell: my.env .docker-build
	./docker/run_tests_in_docker.sh --shell

.PHONY: run
run: my.env
	${DC} up processor webapp webpack oidcprovider

.PHONY: stop
stop: my.env
	${DC} stop

.PHONY: dependencycheck
dependencycheck: my.env
	${DC} run crontabber shell ./docker/run_dependency_checks.sh


# Python 3 migration related things--remove after we've finished migrating

.docker-build3:
	make build3

.PHONY: build3
build3: my.env
	${DC} build --build-arg userid=${SOCORRO_UID} --build-arg groupid=${SOCORRO_GID} testpython3
	touch .docker-build3

.PHONY: lint3
lint3: my.env .docker-build3
	${DC} run --no-deps testpython3 ./docker/run_lint.sh

.PHONY: test3
test3: my.env .docker-build3
	USEPYTHON=3 ./docker/run_tests_in_docker.sh ${ARGS}

.PHONY: testshell3
testshell3: my.env .docker-build3
	USEPYTHON=3 ./docker/run_tests_in_docker.sh --shell
