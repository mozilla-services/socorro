#!/bin/bash
#
# Socorro staging install script
#

. /etc/socorro/socorrorc

lock socorro

if [ $# != 1 ]
then
  echo "Syntax: socorro-install.sh <url-to-socorro_tar_gz>"
  exit 1
fi

URL=$1

# current date to the second, used for archiving old builds
DATE=`date +%d-%m-%Y_%H_%M_%S`
fatal $? "could not set date"

# download latest successful Hudson build
OLD_CSUM=""
if [ -f socorro.tar.gz ]
then
  OLD_CSUM=`md5sum socorro.tar.gz | awk '{print $1}'`
  fatal $? "could not get old checksum"
fi
wget -q -O socorro-new.tar.gz -N $URL
fatal $? "wget reported failure"

NEW_CSUM=`md5sum socorro-new.tar.gz | awk '{print $1}'`
fatal $? "could not get new checksum"

if [ "$OLD_CSUM" == "$NEW_CSUM" ]
then
  exit 0
fi

# untar new build into tmp area
TMP=`mktemp -d /tmp/socorro-install-$$-XXX`
fatal $? "mktemp reported failure"
tar -C ${TMP} -zxf socorro-new.tar.gz
fatal $? "could not untar new Socorro build"

# backup old build
mv /data/socorro /data/socorro.${DATE}
fatal $? "could not backup old Socorro build"

# install new build
mv ${TMP}/socorro/ /data/
fatal $? "could not install new Socorro build"

# move new socorro.tar.gz over old
mv socorro-new.tar.gz socorro.tar.gz

if [ -f /etc/socorro/mware.htpasswd ]
then
  rsync /etc/socorro/mware.htpasswd /data/socorro/application/.htpasswd
  fatal $? "could not copy mware htpasswd into place"
fi

if [ -d /etc/socorro/web/ ]
then
  rsync /etc/socorro/web/*.php /data/socorro/htdocs/application/config/
  fatal $? "could not copy webapp-php configs into place"
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
  /sbin/service httpd restart
  fatal $? "could not start httpd"
fi
cd ${OLD_PWD}

echo "Socorro build installed successfully!"
echo "Downloaded from ${URL}"
echo "Checksum: ${NEW_CSUM}"
echo "Backed up original to /data/socorro.${DATE}"

unlock socorro
