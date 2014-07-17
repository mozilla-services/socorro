#!/bin/bash
#
# Socorro deploy script
#

if [ $# != 1 ]
then
  echo "Syntax: deploy.sh <url-to-socorro_tar_gz>"
  exit 1
fi

URL=$1

grep '6.' /etc/redhat-release &> /dev/null
if [ $? != 0 ]
then
  echo "Only RHEL 6 based Linux distros (CentOS, etc.) are supported"
  exit 1
fi

function error {
  if [ $# != 2 ]
  then
    echo "Syntax: error <exit_code> <message>"
    exit 1
  fi
  EXIT_CODE=$1
  MESSAGE=$2
  if [ $EXIT_CODE != 0 ]
  then
    echo "ERROR: $MESSAGE"
    exit $EXIT_CODE
  fi
}

# Ensure we're executing in the directory we live in, so that we don't
# have different socorro.tar.gz files based on your $PWD when you run
# this script.
cd "$(dirname "$0")"
error $? "could not change working directory"

# current date to the second, used for archiving old builds
DATE=`date +%d-%m-%Y_%H_%M_%S`
error $? "could not set date"

# ensure socorro user exists
id socorro &> /dev/null
if [ $? != 0 ]; then
    echo "Creating socorro user"
    useradd socorro
    error $? "could not create socorro user"
fi

# ensure base directories exist
echo "Creating system config, log and crash storage directories"
mkdir -p /etc/socorro
error $? "could not create /etc/socorro"
mkdir -p /var/log/socorro
error $? "could not create /var/log/socorro"
chown socorro /var/log/socorro
error $? "could not chown /var/log/socorro"
mkdir -p /data/socorro
error $? "could not create /data/socorro"
mkdir -p /var/lock/socorro
error $? "could not create /var/lock/socorro"
chown socorro /var/lock/socorro
error $? "could not chown /var/lock/socorro"
mkdir -p /home/socorro/primaryCrashStore \
    /home/socorro/fallback \
    /home/socorro/persistent
error $? "could not make socorro crash storage directories"
chown apache:socorro /home/socorro/primaryCrashStore /home/socorro/fallback
error $? "could not chown apache on crash storage directories, is httpd installed?"
chmod o+x /home/socorro
error $? "could not chmod o+x socorro homedir"
chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback
error $? "could not chmod crash storage directories"

# download latest successful Jenkins build
OLD_CSUM=""
if [ -f socorro.tar.gz ]
then
  OLD_CSUM=`md5sum socorro.tar.gz | awk '{print $1}'`
  error $? "could not get old checksum"
fi
echo "Downloading socorro.tar.gz"
curl -s -z socorro.tar.gz $URL > socorro-new.tar.gz
error $? "curl reported failure"

if [ ! -s socorro-new.tar.gz ]
then
  echo "No new file available."
  echo "Remove socorro.tar.gz and rerun to override."
  exit 0
fi

NEW_CSUM=`md5sum socorro-new.tar.gz | awk '{print $1}'`
error $? "could not get new checksum"

if [ "$OLD_CSUM" == "$NEW_CSUM" ]
then
  echo "No changes from previous build, aborting"
  echo "(remove socorro.tar.gz and re-run to proceed anyway)"
  exit 0
fi

# untar new build into tmp area
echo "Unpacking new build"
TMP=`mktemp -d /tmp/socorro-install-$$-XXX`
error $? "mktemp reported failure"
tar -C ${TMP} -zxf socorro-new.tar.gz
error $? "could not untar new Socorro build"

# backup old build
echo "Backing up old build to /data/socorro.${DATE}"
mv /data/socorro /data/socorro.${DATE}
error $? "could not backup old Socorro build"

# install new build
echo "Installing new build to /data/socorro"
mv ${TMP}/socorro/ /data/
error $? "could not install new Socorro build"

# deploy system files
cp /data/socorro/application/scripts/crons/socorrorc /etc/socorro/
error $? "could not copy socorrorc"

if [ ! -f /etc/httpd/conf.d/socorro.conf ]; then
    cp /data/socorro/application/config/apache.conf-dist \
        /etc/httpd/conf.d/socorro.conf
    error $? "could not copy socorro apache config"
fi

cp /data/socorro/application/config/*.ini-dist /etc/socorro
error $? "could not copy dist files to /etc/socorro"
pushd /etc/socorro > /dev/null
error $? "could not pushd /etc/socorro"
for file in *.ini-dist; do
    if [ ! -f `basename $file -dist` ]; then
        cp $file `basename $file -dist`
        error $? "could not copy ${file}-dist to $file"
    fi
done
popd > /dev/null

# copy system files into install, to catch any overrides
cp /etc/socorro/*.ini /data/socorro/application/config/
error $? "could not copy /etc/socorro/*.ini into install"
system_localpy="/etc/socorro/local.py"
socorro_localpy="/data/socorro/webapp-django/crashstats/settings/local.py"
if [ ! -f "$system_localpy" ]; then
    cp "$socorro_localpy" "$system_localpy"
    error $? "could not copy initial local.py to /etc/socorro"

    echo
    echo "NOTICE: Please edit the configuration files in /etc/socorro and re-run this script"
    exit 0
fi

if [ -f "$socorro_localpy" ]; then
    mv "$socorro_localpy" "${socorro_localpy}.dist"
    error $? "could not move $socorro_localpy out of the way"
fi

ln -vsf "$system_localpy" "$socorro_localpy"
error $? "could not symlink $system_localpy into install"

# TODO optional support for crashmover
for service in processor
do
  cp /data/socorro/application/scripts/init.d/socorro-${service} /etc/init.d/
  error $? "could not copy socorro-${service} init script"
  chkconfig --add socorro-${service}
  error $? "could not add socorro-${service} init script"
  chkconfig socorro-${service} on
  error $? "could not enable socorro-${service} init script"
done

# create DB if it does not exist
# TODO handle DB not on local device - could use setupdb for this
psql -U postgres -h localhost -l | grep breakpad > /dev/null
if [ $? != 0 ]; then
    echo "Creating new DB, may take a few minutes"
    pushd /data/socorro/application > /dev/null
    error $? "Could not pushd /data/socorro"
    PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
        ./socorro/external/postgresql/setupdb_app.py \
        --database_name=breakpad --fakedata \
        --database_superusername=postgres \
        &> /var/log/socorro/setupdb.log
    error $? "Could not create new fakedata DB `cat /var/log/socorro/setupdb.log`"
    popd > /dev/null
    error $? "Could not popd"
else
    echo "Running database migrations with alembic"
    pushd /data/socorro/application > /dev/null
    error $? "Could not pushd /data/socorro"
    PYTHONPATH=. ../socorro-virtualenv/bin/python \
        ../socorro-virtualenv/bin/alembic \
        -c config/alembic.ini upgrade head &> /var/log/socorro/alembic.log
    error $? "Could not run migrations with alembic"
    popd > /dev/null
    error $? "Could not popd"
fi

# ensure that partitions have been created
pushd /data/socorro/application > /dev/null
error $? "could not pushd /data/socorro/application"
su socorro -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
    socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force \
    --admin.conf=/etc/socorro/crontabber.ini \
    &> /var/log/socorro/crontabber.log"
error $? "could not run crontabber `cat /var/log/socorro/crontabber.log`"
popd > /dev/null

if [ ! -f /etc/cron.d/socorro ]; then
    # crond doesn't like files with executable bits, and doesn't load
    # them.
    chmod 644 /data/socorro/application/config/crontab-dist
    error $? "could not modify socorro crontab permissions"

    cp -a /data/socorro/application/config/crontab-dist \
        /etc/cron.d/socorro
    error $? "could not copy socorro crontab"
fi

# TODO optional support for crashmover
for service in socorro-processor httpd
do
  if [ -f /etc/init.d/${service} ]
  then
    /sbin/service ${service} status > /dev/null
    if [ $? != 0 ]; then
        /sbin/service ${service} start
        error $? "could not start ${service}"
    else
        /sbin/service ${service} restart
        error $? "could not restart ${service}"
    fi
  fi
done

echo "Running Django syncdb"
/data/socorro/socorro-virtualenv/bin/python \
    /data/socorro/webapp-django/manage.py syncdb --noinput \
    &> /var/log/socorro/django-syncdb.log
error $? "django syncdb failed `cat /var/log/socorro/django-syncdb.log`"

# move new socorro.tar.gz over old now that the installation was
# succesful.
mv socorro-new.tar.gz socorro.tar.gz
error $? "could not mv socorro-new.tar.gz -> socorro.tar.gz"

echo "Socorro build installed successfully!"
echo "Downloaded from ${URL}"
echo "Checksum: ${NEW_CSUM}"
echo "Backed up original to /data/socorro.${DATE}"
