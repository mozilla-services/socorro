#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Build script for building Breakpad and stackwalk

# Failures should cause setup to fail
set -v -e -x

pushd /tmp

if [ "$(uname -sm)" == "Linux x86_64" ]; then
    # Pull pre-built, known version of breakpad
    apt-get install -y wget

    wget -N --quiet 'https://index.taskcluster.net/v1/task/project.socorro.breakpad.v1.builds.linux64.latest/artifacts/public/breakpad.tar.gz'
    tar -zxf breakpad.tar.gz
    rm -rf stackwalk
    mv breakpad stackwalk
else
    # Build breakpad
    PREFIX=/tmp/stackwalk/ SKIP_TAR=1 ./build-breakpad.sh
fi

# Now build stackwalk
pushd minidump-stackwalk
make
popd

# Put the final binaries in /stackwalk in the container
mkdir /stackwalk
cp minidump-stackwalk/stackwalker /stackwalk
cp minidump-stackwalk/jit-crash-categorize /stackwalk
cp minidump-stackwalk/dumplookup /stackwalk
