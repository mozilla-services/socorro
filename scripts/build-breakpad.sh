#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Jenkins build script for building Breakpad

# any failures in this script should cause the build to fail
set -e

# Checkout and build Breakpad
echo "PREFIX: ${PREFIX:=`pwd`/build/breakpad}"
svn co http://google-breakpad.googlecode.com/svn/trunk google-breakpad
cd google-breakpad
./configure --prefix=${PREFIX}
make install
if test -z "${SKIP_CHECK}"; then
  #FIXME: Breakpad tests hang on Jenkins CI   
  #make check
  true
fi
svn info | grep Revision | cut -d' ' -f 2 > ${PREFIX}/revision.txt
cd ..

# Clone and build exploitable
if test -d exploitable; then
  hg -R exploitable pull -u
else
  hg clone http://hg.mozilla.org/users/tmielczarek_mozilla.com/exploitable/
fi
cd exploitable
make BREAKPAD_SRCDIR=../google-breakpad BREAKPAD_OBJDIR=../google-breakpad
cp exploitable ${PREFIX}/bin
cd ..

# Optionally package everything up
if test -z "${SKIP_TAR}"; then
  echo "Creating breakpad.tar.gz"
  tar -C ${PREFIX}/.. --mode 755 --owner 0 --group 0 -zcf breakpad.tar.gz `basename ${PREFIX}`
fi
