#!/bin/sh

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Launches bash in a socorro-ized environment to use on the servers. This
# includes the Socorro Python virtualenv as well as pulling in consul
# configuration.
#
# This doesn't work in docker and isn't needed.
#
# Usage:
#
#     /data/socorro/bin/socorro_env.sh

set -e

echo "Activate Python virtualenv..."
# Active virtualenv in this environment
. /data/socorro/socorro-virtualenv/bin/activate

echo "Add all the stuff from envconsul..."
export "$(envconsul -prefix socorro/common -prefix socorro/processor -prefix socorro/webapp -prefix socorro/crontabber env)"

echo "Set prompt..."
export PS1='(socorro) \u@\h:\w\$ '

echo "Launch bash... (type 'exit' when finished)"
/bin/bash
