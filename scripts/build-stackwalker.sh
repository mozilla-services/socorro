#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Build script for building Breakpad and stackwalker

# Failures should cause setup to fail
set -v -e -x

# Destination directory for the final stackwalker binaries
STACKWALKDIR="${STACKWALKDIR:-$(pwd)/stackwalk}"

# Source and build directories
SRCDIR="${SRCDIR:-$(pwd)}"

cd "${SRCDIR}"

# Build breakpad from source; takes about 2 minutes
PREFIX="${SRCDIR}/breakpad/" SKIP_TAR=1 "${SRCDIR}/scripts/build-breakpad.sh"

# Copy breakpad bits into stackwalk/
rm -rf stackwalk || true
cp -r "${SRCDIR}/breakpad" "${SRCDIR}/stackwalk"

# Now build stackwalker
cd "${SRCDIR}/minidump-stackwalk"
make clean
make

# Put the final binaries in STACKWALKDIR
if [ ! -d "${STACKWALKDIR}" ];
then
  mkdir "${STACKWALKDIR}"
fi
cd "${SRCDIR}/minidump-stackwalk/"
cp stackwalker jit-crash-categorize dumplookup "${STACKWALKDIR}"
