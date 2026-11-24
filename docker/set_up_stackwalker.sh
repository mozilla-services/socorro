#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: docker/set_up_stackwalker.sh
#
# Installs the stackwalker.

set -euo pipefail

# This should be a url to a .tar.gz file from the release page:
# https://github.com/rust-minidump/rust-minidump/releases
# TODO(bdanforth): Update this URL once Bug 2054202 is done.
URL="http://host.docker.internal:8000/socorro-stackwalker-84f84cf.2026-11-24.tar.gz"

TARFILE="stackwalker.tar.gz"
TARGETDIR="/stackwalk-rust"
TMPDIR="/tmp/stackwalkerinstall"

mkdir -p "${TMPDIR}"
pushd "${TMPDIR}"

# Download tar file
curl -sL -o "${TARFILE}" "${URL}"
pwd
ls -l "${TARFILE}"

# Untar tarfile and put contents in the right place
tar -xzvf "${TARFILE}"
mkdir -p "${TARGETDIR}" || true
cp build/bin/minidump-stackwalk "${TARGETDIR}"
cp build/minidump-stackwalk.version.json "${TARGETDIR}/minidump-stackwalk.version.json"
cp build/bin/symbolicate-stacks "${TARGETDIR}"
cp build/symbolicate-stacks.version.json "${TARGETDIR}/symbolicate-stacks.version.json"
ls -l "${TARGETDIR}"

# Make sure it runs and reports version
${TARGETDIR}/minidump-stackwalk --version
# symbolicate-stacks doesn't support --version yet, so --help is the "does it run at all" check.
${TARGETDIR}/symbolicate-stacks --help > /dev/null

# Clean up
popd
rm -rf "${TMPDIR}"
