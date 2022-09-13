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
URL="https://github.com/mozilla-services/socorro-stackwalk/releases/download/v20220830.0/socorro-stackwalker.2022-08-30.f9933c36.tar.gz"

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
cp build/stackwalk.version.json "${TARGETDIR}/minidump-stackwalk.version.json"
ls -l "${TARGETDIR}"

# Clean up
popd
rm -rf "${TMPDIR}"
