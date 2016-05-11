#! /bin/bash -e
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Jenkins build script for running tests and packaging build

echo "this is build.sh"

# This variable gets set by travis.
# It can be either of these:
#  webapp
#  socorro
#  end-to-end
#  puppet
SUITE=$1
echo "Testing specifically $SUITE"

if [ "$SUITE" == "socorro" ]; then
    ./scripts/test.sh
fi

if [ "$SUITE" == "webapp" ]; then
    ./scripts/test-webapp.sh
fi

if [ "$SUITE" == "puppet" ]; then
    ./scripts/test-webapp.sh
fi

if [ "$SUITE" == "end-to-end" ]; then
    ./scripts/integration-test.sh --destroy
fi
