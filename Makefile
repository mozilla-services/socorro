# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

PREFIX=/data/socorro
ABS_PREFIX = $(shell readlink -f $(PREFIX))
VIRTUALENV=$(CURDIR)/socorro-virtualenv
PYTHONPATH = "."
NOSE = $(VIRTUALENV)/bin/nosetests socorro -s --with-xunit
SETUPDB = $(VIRTUALENV)/bin/python ./socorro/external/postgresql/setupdb_app.py
COVEROPTS = --with-coverage --cover-package=socorro
COVERAGE = $(VIRTUALENV)/bin/coverage
PYLINT = $(VIRTUALENV)/bin/pylint
JENKINS_CONF = jenkins.py.dist
ENV = env

PG_RESOURCES = $(if $(database_hostname), resource.postgresql.database_hostname=$(database_hostname)) $(if $(database_username), secrets.postgresql.database_username=$(database_username)) $(if $(database_password), secrets.postgresql.database_password=$(database_password)) $(if $(database_port), resource.postgresql.database_port=$(database_port))
RMQ_RESOURCES = $(if $(rmq_host), resource.rabbitmq.host=$(rmq_host)) $(if $(rmq_virtual_host), resource.rabbitmq.virtual_host=$(rmq_virtual_host)) $(if $(rmq_user), secrets.rabbitmq.rabbitmq_user=$(rmq_user)) $(if $(rmq_password), secrets.rabbitmq.rabbitmq_password=$(rmq_password))
ES_RESOURCES = $(if $(elasticsearch_urls), resource.elasticsearch.elasticsearch_urls=$(elasticsearch_urls))

.PHONY: all test test-socorro test-webapp bootstrap install reinstall install-socorro lint clean breakpad stackwalker analysis json_enhancements_pg_extension webapp-django

all:	test

test: test-socorro test-webapp

test-socorro: bootstrap
	# jenkins only settings for the pre-configman components
	# can be removed when all tests are updated to use configman
	if [ $(WORKSPACE) ]; then cd socorro/unittest/config; cp $(JENKINS_CONF) commonconfig.py; fi;
	# setup any unset test configs and databases without overwriting existing files
	cd config; for file in *.ini-dist; do if [ ! -f `basename $$file -dist` ]; then cp $$file `basename $$file -dist`; fi; done
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_integration_test --database_username=$(database_username) --database_hostname=$(database_hostname) --database_password=$(database_password) --database_port=$(DB_PORT) --database_superusername=$(database_superusername) --database_superuserpassword=$(database_superuserpassword) --dropdb --logging.stderr_error_logging_level=40 --unlogged
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_test --database_username=$(database_username) --database_hostname=$(database_hostname) --database_password=$(database_password) --database_port=$(DB_PORT) --database_superusername=$(database_superusername) --database_superuserpassword=$(database_superuserpassword) --dropdb --no_schema --logging.stderr_error_logging_level=40 --unlogged
	cd socorro/unittest/config; for file in *.py.dist; do if [ ! -f `basename $$file .dist` ]; then cp $$file `basename $$file .dist`; fi; done
	# run tests with coverage
	rm -f coverage.xml
	$(ENV) $(PG_RESOURCES) $(RMQ_RESOURCES) $(ES_RESOURCES) PYTHONPATH=$(PYTHONPATH) $(COVERAGE) run $(NOSE)
	$(COVERAGE) xml

# makes thing semantically consistent (test-{component}) while avoiding
# building the webapp twice to save a little time
test-webapp: webapp-django
	# alias to webapp-django

bootstrap:
	git submodule update --init --recursive
	if [[ ! "$$(type -p lessc)" ]]; then printf "\e[0;32mlessc not found! less must be installed and lessc on your path to build socorro.\e[0m\n" && exit 1; fi;
	[ -d $(VIRTUALENV) ] || virtualenv -p python2.6 $(VIRTUALENV)
	# install dev + prod dependencies
	$(VIRTUALENV)/bin/pip install tools/peep-0.8.tar.gz
	$(VIRTUALENV)/bin/peep install --download-cache=./pip-cache -r requirements.txt

install: bootstrap reinstall

# this a dev-only option, `make install` needs to be run at least once in the checkout (or after `make clean`)
reinstall: install-socorro
	# record current git revision in install dir
	git rev-parse HEAD > $(PREFIX)/application/socorro/external/postgresql/socorro_revision.txt
	cp $(PREFIX)/stackwalk/revision.txt $(PREFIX)/application/socorro/external/postgresql/breakpad_revision.txt

install-socorro: webapp-django
	# package up the tarball in $(PREFIX)
	# create base directories
	mkdir -p $(PREFIX)/application
	# copy to install directory
	rsync -a config $(PREFIX)/application
	rsync -a $(VIRTUALENV) $(PREFIX)
	rsync -a socorro $(PREFIX)/application
	rsync -a scripts $(PREFIX)/application
	rsync -a tools $(PREFIX)/application
	rsync -a sql $(PREFIX)/application
	rsync -a wsgi $(PREFIX)/application
	rsync -a stackwalk $(PREFIX)/
	rsync -a scripts/stackwalk.sh $(PREFIX)/stackwalk/bin/
	rsync -a analysis $(PREFIX)/
	rsync -a alembic $(PREFIX)/application
	# purge the virtualenv
	[ -d webapp-django/virtualenv ] || rm -rf webapp-django/virtualenv
	rsync -a webapp-django $(PREFIX)/
	# copy default config files
	cd $(PREFIX)/application/scripts/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done

lint:
	rm -f pylint.txt
	$(PYLINT) -f parseable --rcfile=pylintrc socorro > pylint.txt

clean:
	find ./socorro/ -type f -name "*.pyc" -exec rm {} \;
	rm -rf ./google-breakpad/ ./builds/ ./breakpad/ ./stackwalk ./pip-cache
	rm -rf ./breakpad.tar.gz
	cd minidump-stackwalk; make clean

breakpad:
	PREFIX=`pwd`/stackwalk/ SKIP_TAR=1 ./scripts/build-breakpad.sh

analysis: bootstrap
	git submodule update --init socorro-toolbox akela
	cd akela && mvn package
	cd socorro-toolbox && mvn package
	mkdir -p analysis
	rsync socorro-toolbox/target/*.jar analysis/
	rsync akela/target/*.jar analysis/
	rsync -a socorro-toolbox/src/main/pig/ analysis/

json_enhancements_pg_extension: bootstrap
    # This is only run manually, as it is a one-time operation
    # to be performed at system installation time, rather than
    # every time Socorro is built
	if [ ! -f `pg_config --pkglibdir`/json_enhancements.so ]; then sudo env PATH=$$PATH $(VIRTUALENV)/bin/python -c "from pgxnclient import cli; cli.main(['install', 'json_enhancements'])"; fi

webapp-django: bootstrap
	cd webapp-django; ./bin/jenkins.sh

stackwalker:
	# Build JSON stackwalker
	# Depends on breakpad, run "make breakpad" if you don't have it yet
	cd minidump-stackwalk; make
	cp minidump-stackwalk/stackwalker stackwalk/bin
