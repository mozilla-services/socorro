#! /bin/bash -e

if [ -n $BUILD_NUMBER ]
then
  echo "$BUILD_NUMBER" > builds/socorro/JENKINS_BUILD_NUMBER
fi
tar -C builds --mode 755 --exclude-vcs --owner 0 --group 0 -zcf socorro.tar.gz socorro/
