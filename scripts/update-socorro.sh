#!/bin/bash
#
# Socorro staging install script
#

. /etc/socorro/socorrorc

lock socorro

if [ $# != 1 ]
then
  echo "Syntax: socorro-install.sh <url-to-socorro_tar_gz>"
  unlock socorro
  exit 1
fi

URL=$1

# current date to the second, used for archiving old builds
DATE=`date +%d-%m-%Y_%H_%M_%S`
fatal $? "could not set date"

# download latest successful Hudson build
OLD_CSUM=""
if [ -f socorro-old.tar.gz ]
then
  OLD_CSUM=`md5sum socorro-old.tar.gz | awk '{print $1}'`
  fatal $? "could not get old checksum"
fi

if [ -f socorro.tar.gz ]
then
  rm socorro.tar.gz
fi

wget -q $URL
fatal $? "wget reported failure"

NEW_CSUM=`md5sum socorro.tar.gz | awk '{print $1}'`
fatal $? "could not get new checksum"

if [ "$OLD_CSUM" == "$NEW_CSUM" ]
then
  unlock socorro
  exit 0
fi

# untar new build into tmp area
TMP=`mktemp -d /tmp/socorro-install-$$-XXX`
fatal $? "mktemp reported failure"
tar -C ${TMP} -zxf socorro.tar.gz
fatal $? "could not untar new Socorro build"

# backup old build
mv /data/socorro /data/socorro.${DATE}
fatal $? "could not backup old Socorro build"

# install new build
mv ${TMP}/socorro/ /data/
fatal $? "could not install new Socorro build"

if [ -f /etc/socorro/mware.htpasswd ]
then
  rsync /etc/socorro/mware.htpasswd /data/socorro/application/.htpasswd
  fatal $? "could not copy mware htpasswd into place"
fi

OLD_PWD=$PWD
if [ -f /etc/init.d/socorro-crashmover ]
then
  /sbin/service socorro-crashmover restart
  fatal $? "could not start socorro-crashmover"
fi
if [ -f /etc/init.d/socorro-processor ]
then
  /sbin/service socorro-processor restart
  fatal $? "could not start socorro-processor"
fi
if [ -f /etc/init.d/socorro-monitor ]
then
  /sbin/service socorro-monitor restart
  fatal $? "could not start socorro-monitor"
fi
if [ -f /etc/init.d/httpd ]
then
  /sbin/service httpd graceful
  fatal $? "could not start httpd"
fi
if [ -f /etc/init.d/memcached ]
then
  echo 'flush_all' | nc -v localhost 11211
  fatal $? "could not flush memcached"
fi
cd ${OLD_PWD}

echo "Socorro build installed successfully!"
echo "Downloaded from ${URL}"
echo "Checksum: ${NEW_CSUM}"
echo "Backed up original to /data/socorro.${DATE}"

cp socorro.tar.gz socorro-old.tar.gz
unlock socorro
