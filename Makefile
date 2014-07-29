# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

.PHONY: all test bootstrap install lint clean breakpad stackwalker json_enhancements_pg_extension

all: test

test: bootstrap
	bash ./scripts/test.sh

bootstrap:
	bash ./scripts/bootstrap.sh

install: bootstrap
	bash ./scripts/install.sh

lint:
	bash ./scripts/lint.sh

clean:
	bash ./scripts/clean.sh

breakpad:
	PREFIX=`pwd`/stackwalk/ SKIP_TAR=1 ./scripts/build-breakpad.sh

json_enhancements_pg_extension: bootstrap
	bash ./scripts/json-enhancements.sh

stackwalker:
	# Build JSON stackwalker
	# Depends on breakpad, run "make breakpad" if you don't have it yet
	cd minidump-stackwalk; make
	cp minidump-stackwalk/stackwalker stackwalk/bin
