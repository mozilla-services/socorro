#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Build script for building Breakpad and stackwalk

# Failures should cause setup to fail
set -v -e -x

pushd /tmp

# First build breakpad
PREFIX=/tmp/stackwalk/ SKIP_TAR=1 ./build-breakpad.sh

# Now build stackwalk
pushd minidump-stackwalk
make
popd
# FIXME(willkg): do we want to copy these binary things somewhere less "tmp"?
cp minidump-stackwalk/stackwalker stackwalk/bin
cp minidump-stackwalk/jit-crash-categorize stackwalk/bin
cp minidump-stackwalk/dumplookup stackwalk/bin
