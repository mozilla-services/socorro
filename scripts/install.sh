#! /bin/bash -ex

export BUILD_DIR=${BUILD_DIR:-builds/socorro}
export SOCORRO_DIR=${BUILD_DIR}/data/socorro

# create base directories
mkdir -p $BUILD_DIR/etc/init.d
mkdir -p $BUILD_DIR/etc/cron.d
mkdir -p $BUILD_DIR/etc/httpd/conf.d

mkdir -p $SOCORRO_DIR
mkdir -p $BUILD_DIR/etc/socorro
mkdir -p $BUILD_DIR/var/log/socorro
mkdir -p $BUILD_DIR/var/lock/socorro


# copy default config files
for file in scripts/config/*.py.dist; do
  cp $file $BUILD_DIR/etc/socorro/`basename $file .dist`
done

for file in config/*.ini-dist; do
  cp $file $BUILD_DIR/etc/socorro/`basename $file -dist`
done

cp scripts/crons/socorrorc $BUILD_DIR/etc/socorro/
for service in processor
do
    cp scripts/init.d/socorro-${service} $BUILD_DIR/etc/init.d/
done
cp config/crontab-dist $BUILD_DIR/etc/cron.d/socorro
cp webapp-django/crashstats/settings/local.py $BUILD_DIR/etc/socorro/local.py
cp config/apache.conf-dist $BUILD_DIR/etc/httpd/conf.d/socorro.conf

# copy to install directory
rsync -a ${VIRTUAL_ENV} $SOCORRO_DIR/
rsync -a socorro $SOCORRO_DIR/application
rsync -a scripts $SOCORRO_DIR/application
rsync -a tools $SOCORRO_DIR/application
rsync -a sql $SOCORRO_DIR/application
rsync -a wsgi $SOCORRO_DIR/application
rsync -a stackwalk $SOCORRO_DIR/
rsync -a scripts/stackwalk.sh $SOCORRO_DIR/stackwalk/bin/
rsync -a analysis $SOCORRO_DIR/
rsync -a alembic $SOCORRO_DIR/application
rsync -a webapp-django $SOCORRO_DIR/


# record current git revision in install dir
git rev-parse HEAD > $SOCORRO_DIR/application/socorro/external/postgresql/socorro_revision.txt
cp $SOCORRO_DIR/stackwalk/revision.txt $SOCORRO_DIR/application/socorro/external/postgresql/breakpad_revision.txt

# Write down build number, if ran by Jenkins
if [ -n "$BUILD_NUMBER" ]
then
  echo "$BUILD_NUMBER" > $SOCORRO_DIR/JENKINS_BUILD_NUMBER
fi
