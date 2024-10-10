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

DOCKER := $(shell which docker)
DC=${DOCKER} compose

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

.devcontainer-build:
	make devcontainerbuild

.PHONY: build
build: my.env  ## | Build docker images.
	${DC} build ${DOCKER_BUILD_OPTS} --build-arg userid=${SOCORRO_UID} --build-arg groupid=${SOCORRO_GID} --progress plain app
	${DC} build --progress plain oidcprovider fakesentry gcs-emulator
	${DC} build --progress plain statsd postgresql memcached elasticsearch symbolsserver
	touch .docker-build

.PHONY: devcontainerbuild
devcontainerbuild: my.env  ## | Build VS Code development container.
	${DC} build devcontainer
	touch .devcontainer-build

.PHONY: devcontainer
devcontainer: my.env .devcontainer-build  ## | Run VS Code development container.
	${DC} up --detach devcontainer

.PHONY: setup
setup: my.env .docker-build  ## | Set up Postgres, Elasticsearch, local Pub/Sub, and local GCS services.
	${DC} run --rm app shell /app/bin/setup_services.sh

.PHONY: updatedata
updatedata: my.env  ## | Add/update necessary database data.
	${DC} run --rm app shell /app/bin/update_data.sh

.PHONY: run
run: my.env  ## | Run processor, webapp, fakesentry, symbolsserver, and required services.
	${DC} up \
		--attach processor \
		--attach webapp \
		--attach fakesentry \
		--attach symbolsserver \
		processor webapp fakesentry symbolsserver

.PHONY: runservices
runservices: my.env  ## | Run service containers (Postgres, Pub/Sub, etc)
	${DC} up -d --remove-orphans \
		elasticsearch \
		gcs-emulator \
		memcached \
		postgresql \
		pubsub \
		statsd \
		symbolsserver

.PHONY: runsubmitter
runsubmitter: my.env  ## | Run stage_submitter and fakecollector
	${DC} up \
		--attach stage_submitter \
		--attach fakecollector \
		stage_submitter fakecollector

.PHONY: stop
stop: my.env  ## | Stop all service containers.
	${DC} stop

.PHONY: shell
shell: my.env .docker-build  ## | Open a shell in the app container.
	${DC} run --rm --entrypoint /bin/bash app

.PHONY: clean
clean:  ## | Remove all build, test, coverage, and Python artifacts.
	-rm .docker-build*
	-rm -rf .cache
	@echo "Skipping deletion of symbols/ in case you have data in there."

.PHONY: docs
docs: my.env .docker-build  ## | Generate Sphinx HTML documetation.
	${DC} run --rm --user ${SOCORRO_UID} app shell make -C docs/ clean
	${DC} run --rm --user ${SOCORRO_UID} app shell make -C docs/ html

.PHONY: lint
lint: my.env  ## | Lint code.
	${DC} run --rm --no-deps app shell ./bin/lint.sh

.PHONY: lintfix
lintfix: my.env  ## | Reformat code.
	${DC} run --rm --no-deps app shell ./bin/lint.sh --fix

.PHONY: psql
psql: my.env .docker-build  ## | Open psql cli.
	@echo "NOTE: Password is 'postgres'."
	${DC} run --rm postgresql psql -h postgresql -U postgres -d socorro

.PHONY: test
test: my.env .docker-build  ## | Run unit tests.
	${DC} run --rm test shell ./bin/test.sh

.PHONY: test-ci
test-ci: my.env .docker-build  ## | Run unit tests in CI.
	# Run tests in test-ci which doesn't volume mount local directory
	${DC} run --rm test-ci shell ./bin/test.sh

.PHONY: testshell
testshell: my.env .docker-build  ## | Open a shell in the test environment.
	${DC} run --rm --entrypoint /bin/bash test

.PHONY: rebuildreqs
rebuildreqs: .env .docker-build  ## | Rebuild requirements.txt file after requirements.in changes.
	${DC} run --rm --no-deps app shell pip-compile --generate-hashes --strip-extras
	${DC} run --rm --no-deps app shell pip-compile --generate-hashes \
		--unsafe-package=python-dateutil --unsafe-package=six --unsafe-package=urllib3 legacy-es-requirements.in

.PHONY: updatereqs
updatereqs: .env .docker-build  ## | Update deps in requirements.txt file.
	${DC} run --rm --no-deps app shell pip-compile --generate-hashes --strip-extras --upgrade
