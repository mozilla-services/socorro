#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This script can be used to build a new breakpad.tar.gz for Socorro
# under Taskcluster. It is not currently used in an automated fashion,
# you must manually submit a task to get a new build. The simplest way
# is to paste the contents of the following here document into
# the task-creator tool: https://tools.taskcluster.net/task-creator/
#
# This task will update a Taskcluster index if it succeeds, such that
# the most recent tarball can be fetched from:
# https://index.taskcluster.net/v1/task/project.socorro.breakpad.v1.builds.linux64.latest/artifacts/public/breakpad.tar.gz
#
# You must be a member of the `socorro` project in Taskcluster for this
# task to work properly.
#
# NOTE: If you build a snapshot against a newer revision of Breakpad,
#  update BREAKPAD_REV in build-breakpad.sh to match!
: <<'EOF'
created: '2017-04-11T14:17:56.960Z'
deadline: '2017-04-11T15:17:56.960Z'
provisionerId: aws-provisioner-v1
workerType: gecko-misc
retries: 0
expires: '2020-01-01T00:00:00.000Z'
routes:
  - index.project.socorro.breakpad.v1.builds.linux64.latest
scopes:
  - 'queue:route:index.project.socorro.breakpad.v1.builds.linux64.latest'
payload:
  image: 'taskcluster/desktop-build:0.1.11'
  command:
    - /bin/sh
    - '-c'
    - >-
      curl
      "https://raw.githubusercontent.com/${SOCORRO_FORK:=mozilla/socorro}/${SOCORRO_BRANCH:=master}/scripts/breakpad-taskcluster.sh"
      | bash
  artifacts:
    public/breakpad.tar.gz:
      type: file
      path: /home/worker/breakpad.tar.gz
  maxRunTime: 7200
metadata:
  name: Build Breakpad
  description: Build Breakpad for Socorro consumption
  owner: ted@mielczarek.org
  source: 'http://tools.taskcluster.net/task-creator/'
EOF

set -v -e -x

# This script runs in the desktop-build image, but its default python is
# ancient. It does have Python 2.7 installed.
if [[ `python -V 2>&1` = *2.6* ]]; then
  mkdir -p bin
  ln -s /usr/bin/python2.7 bin/python
  export PATH=`pwd`/bin:$PATH
fi

# Its GCC is also ancient, use the tooltool GCC that Firefox uses.
wget https://raw.githubusercontent.com/mozilla/build-tooltool/master/tooltool.py
wget https://hg.mozilla.org/mozilla-central/raw-file/2d59367c985a/browser/config/tooltool-manifests/linux64/releng.manifest
python tooltool.py -m releng.manifest fetch gcc.tar.xz
export CC=`pwd`/gcc/bin/gcc
export CXX=`pwd`/gcc/bin/g++
export PATH=`pwd`/gcc/bin:$PATH

# Defer to the build-breakpad.sh script to do the actual build once the
# environment is set up.
curl "https://raw.githubusercontent.com/${SOCORRO_FORK:=mozilla/socorro}/${SOCORRO_BRANCH:=master}/scripts/build-breakpad.sh" > build-breakpad.sh
bash build-breakpad.sh
