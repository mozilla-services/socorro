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

.PHONY: all test install reinstall install-socorro install-web virtualenv coverage lint clean minidump_stackwalk analysis thirdparty


all:	test

setup-test: virtualenv
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_integration_test --database_username=$(DB_USER) --database_hostname=$(DB_HOST) --database_password=$(DB_PASSWORD) --database_port=$(DB_PORT) --dropdb
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_test --database_username=$(DB_USER) --database_hostname=$(DB_HOST) --database_password=$(DB_PASSWORD) --database_port=$(DB_PORT) --dropdb --no_schema
	cd socorro/unittest/config; for file in *.py.dist; do if [ ! -f `basename $$file .dist` ]; then cp $$file `basename $$file .dist`; fi; done

test: setup-test
	PYTHONPATH=$(PYTHONPATH) $(NOSE)

thirdparty:
	[ -d $(VIRTUALENV) ] || virtualenv -p python2.6 $(VIRTUALENV)
	# install production dependencies
	$(VIRTUALENV)/bin/pip install --use-mirrors --download-cache=pip-cache/ --ignore-installed --install-option="--prefix=`pwd`/thirdparty" --install-option="--install-lib=`pwd`/thirdparty" -r requirements/prod.txt

install: thirdparty reinstall

# this a dev-only option, `make install` needs to be run at least once in the checkout (or after `make clean`)
reinstall: install-socorro install-web
	# record current git revision in install dir
	git rev-parse HEAD > $(PREFIX)/revision.txt
	REV=`cat $(PREFIX)/revision.txt` && sed -ibak "s/CURRENT_SOCORRO_REVISION/$$REV/" $(PREFIX)/application/scripts/config/revisionsconfig.py
	REV=`cat $(PREFIX)/stackwalk/revision.txt` && sed -ibak "s/CURRENT_BREAKPAD_REVISION/$$REV/" $(PREFIX)/application/scripts/config/revisionsconfig.py

install-socorro:
	# create base directories
	mkdir -p $(PREFIX)/htdocs
	mkdir -p $(PREFIX)/application
	# copy to install directory
	rsync -a config $(PREFIX)/application
	rsync -a thirdparty $(PREFIX)
	rsync -a socorro $(PREFIX)/application
	rsync -a scripts $(PREFIX)/application
	rsync -a tools $(PREFIX)/application
	rsync -a sql $(PREFIX)/application
	rsync -a wsgi $(PREFIX)/application
	rsync -a stackwalk $(PREFIX)/
	rsync -a scripts/stackwalk.sh $(PREFIX)/stackwalk/bin/
	rsync -a analysis $(PREFIX)/
	rsync -a alembic $(PREFIX)/application
	# copy default config files
	cd $(PREFIX)/application/scripts/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done

install-web:
	rsync -a --exclude="tests" webapp-php/ $(PREFIX)/htdocs
	cd $(PREFIX)/htdocs/modules/auth/config/; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs/modules/recaptcha/config; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs/application/config; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs; cp htaccess-dist .htaccess

virtualenv:
	[ -e $(VIRTUALENV) ] || virtualenv -p python2.6 $(VIRTUALENV)
	$(VIRTUALENV)/bin/pip install --use-mirrors --download-cache=./pip-cache -r requirements/dev.txt

coverage: setup-test
	rm -f coverage.xml
	PYTHONPATH=$(PYTHONPATH) $(COVERAGE) run $(NOSE)
	$(COVERAGE) xml

lint:
	rm -f pylint.txt
	$(PYLINT) -f parseable --rcfile=pylintrc socorro > pylint.txt

clean:
	find ./socorro/ -type f -name "*.pyc" -exec rm {} \;
	rm -rf ./thirdparty/*
	rm -rf ./google-breakpad/ ./builds/ ./breakpad/ ./stackwalk ./pip-cache
	rm -rf ./breakpad.tar.gz

minidump_stackwalk:
	PREFIX=`pwd`/stackwalk/ SKIP_TAR=1 ./scripts/build-breakpad.sh

analysis:
	git submodule update --init socorro-toolbox akela
	cd akela && mvn package
	cd akela && mvn package
	cd socorro-toolbox && mvn package
	mkdir -p analysis
	rsync socorro-toolbox/target/*.jar analysis/
	rsync akela/target/*.jar analysis/
	rsync -a socorro-toolbox/src/main/pig/ analysis/
