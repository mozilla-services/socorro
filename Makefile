PREFIX=/data/socorro
ABS_PREFIX = $(shell readlink -f $(PREFIX))
VIRTUALENV=$(CURDIR)/socorro-virtualenv
PYTHONPATH = ".:thirdparty"
NOSE = $(VIRTUALENV)/bin/nosetests socorro -s --with-xunit
COVEROPTS = --with-coverage --cover-package=socorro
COVERAGE = $(VIRTUALENV)/bin/coverage
PYLINT = $(VIRTUALENV)/bin/pylint

.PHONY: all test phpunit install reinstall install-socorro install-web virtualenv coverage lint clean minidump_stackwalk java_analysis


all:	test

test: virtualenv phpunit
	PYTHONPATH=$(PYTHONPATH) $(NOSE)

phpunit:
	phpunit webapp-php/tests/

install: java_analysis reinstall

# this a dev-only option, `java_analysis` needs to be run at least once in the checkout (or after `make clean`)
reinstall: install-socorro install-web install-submodules
	# record current git revision in install dir
	git rev-parse HEAD > $(PREFIX)/revision.txt
	REV=`cat $(PREFIX)/revision.txt` && sed -ibak "s/CURRENT_SOCORRO_REVISION/$$REV/" $(PREFIX)/htdocs/application/config/revision.php

install-socorro:
	# create base directories
	mkdir -p $(PREFIX)/htdocs
	mkdir -p $(PREFIX)/application
	rsync -a thirdparty $(PREFIX)
	rsync -a socorro $(PREFIX)/application
	rsync -a scripts $(PREFIX)/application
	rsync -a tools $(PREFIX)/application
	rsync -a sql $(PREFIX)/application
	rsync -a stackwalk $(PREFIX)/
	rsync -a scripts/stackwalk.sh $(PREFIX)/stackwalk/bin/
	rsync -a analysis/build/lib/socorro-analysis-job.jar $(PREFIX)/analysis/
	rsync -a analysis/bin/modulelist.sh $(PREFIX)/analysis/
	cd $(PREFIX)/application/scripts/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done

install-web:
	rsync -a --exclude="tests" webapp-php/ $(PREFIX)/htdocs
	cd $(PREFIX)/htdocs/modules/auth/config/; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs/modules/recaptcha/config; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs/application/config; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs; cp htaccess-dist .htaccess

install-submodules:
	# clone submodule dependencies
	git submodule update --init --recursive configman
	cd configman; python setup.py install --install-lib=$(ABS_PREFIX)/application

virtualenv:
	virtualenv $(VIRTUALENV)
	$(VIRTUALENV)/bin/pip install -r requirements.txt
	cd configman; $(VIRTUALENV)/bin/python setup.py install

coverage: virtualenv phpunit
	rm -f coverage.xml
	cd socorro/unittest/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done
	PYTHONPATH=$(PYTHONPATH) $(COVERAGE) run $(NOSE); $(COVERAGE) xml

lint:
	rm -f pylint.txt
	$(PYLINT) -f parseable --rcfile=pylintrc socorro > pylint.txt

clean:
	find ./socorro/ -type f -name "*.pyc" -exec rm {} \;
	find ./thirdparty/ -type f -name "*.pyc" -exec rm {} \;
	rm -rf ./google-breakpad/ ./builds/ ./breakpad/ ./stackwalk
	rm -rf ./breakpad.tar.gz
	cd analysis && ant clean

minidump_stackwalk:
	svn co http://google-breakpad.googlecode.com/svn/trunk google-breakpad
	cd google-breakpad && ./configure --prefix=`pwd`/../stackwalk/
	cd google-breakpad && make install

java_analysis:
	cd analysis && ant hadoop-jar

