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

# Set this in the environment to force --no-cache docker builds.
DOCKER_BUILD_OPTS :=
ifeq (1, ${NOCACHE})
DOCKER_BUILD_OPTS := --no-cache
endif

DC := $(shell which docker-compose)

.DEFAULT_GOAL := help
.PHONY: help
help:
	@echo "Usage: make RULE"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' Makefile \
		| grep -v grep \
	    | sed -n 's/^\(.*\): \(.*\)##\(.*\)/\1\3/p' \
	    | column -t  -s '|'
	@echo ""
	@echo "See https://socorro.readthedocs.io/ for more documentation."

my.env:
	@if [ ! -f my.env ]; \
	then \
	echo "Copying my.env.dist to my.env..."; \
	cp docker/config/my.env.dist my.env; \
	fi

.docker-build:
	make build

.PHONY: build
build: my.env  ## | Build docker images.
	${DC} build ${DOCKER_BUILD_OPTS} --build-arg userid=${SOCORRO_UID} --build-arg groupid=${SOCORRO_GID} app
	${DC} build oidcprovider
	touch .docker-build

.docker-build-docs:
	make build-docs

.PHONY: build-docs
build-docs: my.env
	${DC} build ${DOCKER_BUILD_OPTS} --build-arg userid=${SOCORRO_UID} --build-arg groupid=${SOCORRO_GID} docs
	touch .docker-build-docs

.PHONY: setup
setup: my.env .docker-build  ## | Set up Postgres, Elasticsearch, local SQS, and local S3 services.
	${DC} run --rm app shell /app/bin/setup_services.sh

.PHONY: updatedata
updatedata: my.env  ## | Add/update necessary database data.
	${DC} run --rm app shell /app/bin/update_data.sh

.PHONY: run
run: my.env  ## | Run processor and webapp and all required services.
	${DC} up processor webapp

.PHONY: runservices
runservices: my.env  ## | Run service containers (Postgres, SQS, etc)
	${DC} up -d statsd postgresql memcached localstack elasticsearch

.PHONY: stop
stop: my.env  ## | Stop all service containers.
	${DC} stop

.PHONY: shell
shell: my.env .docker-build  ## | Open a shell in the app container.
	${DC} run --rm app shell

.PHONY: clean
clean:  ## | Remove all build, test, coverage, and Python artifacts.
	-rm .docker-build*
	-rm -rf .cache

.PHONY: docs
docs: my.env .docker-build-docs  ## | Generate Sphinx HTML documetation.
	${DC} run --rm --user ${SOCORRO_UID} docs make -C docs/ html

.PHONY: lint
lint: my.env  ## | Lint code.
	${DC} run --rm --no-deps app shell ./bin/lint.sh

.PHONY: lintfix
lintfix: my.env  ## | Reformat code.
	${DC} run --rm --no-deps app shell ./bin/lint.sh --fix

.PHONY: test
test: my.env .docker-build  ## | Run unit tests.
	# Make sure services are started and start localstack before the others to
	# give it a little more time to wake up
	${DC} up -d localstack
	${DC} up -d elasticsearch postgresql statsd
	# Run tests
	${DC} run --rm test shell ./bin/test.sh

.PHONY: test-ci
test-ci: my.env .docker-build  ## | Run unit tests in CI.
	# Make sure services are started and start localstack before the others to
	# give it a little more time to wake up
	${DC} up -d localstack
	${DC} up -d elasticsearch postgresql statsd
	# Run tests in test-ci which doesn't volume mount local directory
	${DC} run --rm test-ci shell ./bin/test.sh

.PHONY: testshell
testshell: my.env .docker-build  ## | Open a shell in the test environment.
	${DC} run --rm test shell

.PHONY: rebuildreqs
rebuildreqs: .env .docker-build  ## | Rebuild requirements.txt file after requirements.in changes.
	docker-compose run --rm app shell pip-compile --generate-hashes

.PHONY: updatereqs
updatereqs: .env .docker-build  ## | Update deps in requirements.txt file.
	docker-compose run --rm app shell pip-compile --generate-hashes -U
