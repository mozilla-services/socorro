#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Build script for building Breakpad
#
# Generally run in Taskcluster, but split out to a separate script so it can be
# run for local builds if necessary without assuming the Taskcluster
# environment.

# Failures in this script should cause the build to fail
set -v -e -x

# Build the revision used in the snapshot unless otherwise specified.
# Update this if you update the snapshot!
: BREAKPAD_REV         "${BREAKPAD_REV:=1459e5df74dd03b7d3d473e6d271413d7aa98a88}"

export MAKEFLAGS
MAKEFLAGS=-j$(getconf _NPROCESSORS_ONLN)

if [ ! -d "depot_tools" ]; then
  git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
fi

cd depot_tools || exit
git pull origin master
echo ">>> using depot_tools version: $(git rev-parse HEAD)"
cd ..

# Breakpad will rely on a bunch of stuff from depot_tools, like fetch
# so we just put it on the path
# see  https://chromium.googlesource.com/breakpad/breakpad/+/master/#Getting-started-from-master
export PATH
PATH=$(pwd)/depot_tools:$PATH

# depot_tools only work in Python 2 and it uses "/usr/bin/env python", so
# we take advantage of depot_tools being first in the PATH and create a
# symlink to the happy Python if "python" is Python 3.
PYV=$(python -c "import sys; print(sys.version_info[0]);")
if [ "${PYV}" == "3" ]; then
  echo "'/usr/bin/env python' is Python 3, so making symlink to python2"
  ln -s /usr/bin/python2 $(pwd)/depot_tools/python
fi

# Checkout and build Breakpad
echo "PREFIX: ${PREFIX:=$(pwd)/build/breakpad}"
if [ ! -d "breakpad" ]; then
  mkdir breakpad
  cd breakpad
  fetch breakpad
else
  cd breakpad/src
  git fetch origin
  cd ..
fi

cd src
git checkout "$BREAKPAD_REV"
gclient sync

echo ">>> using breakpad version: $(git rev-parse HEAD)"

mkdir -p "${PREFIX}"
rsync -a --exclude="*.git" ./src "${PREFIX}"/
./configure --prefix="${PREFIX}"
make install
if test -z "${SKIP_CHECK}"; then
  #FIXME: get this working again
  #make check
  true
fi
git rev-parse HEAD > "${PREFIX}"/revision.txt
cd ../..

cp breakpad/src/src/third_party/libdisasm/libdisasm.a "${PREFIX}"/lib/

# Optionally package everything up
if test -z "${SKIP_TAR}"; then
  tar -C "${PREFIX}"/.. -zcf breakpad.tar.gz "$(basename "${PREFIX}")"
fi
