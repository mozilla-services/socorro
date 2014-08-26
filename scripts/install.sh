#! /bin/bash -ex

export BUILD_DIR=${BUILD_DIR:-builds/socorro}

# package up the tarball in $BUILD_DIR
# create base directories
mkdir -p $BUILD_DIR/application
mkdir -p $BUILD_DIR/etc/socorro
mkdir -p $BUILD_DIR/var/log/socorro
mkdir -p $BUILD_DIR/var/lock/socorro
mkdir -p $BUILD_DIR/data/socorro

# copy default config files
pushd config
for file in *.py.dist; do
  cp $file $BUILD_DIR/etc/soccoro/`basename $file .dist`
done
for file in *.ini-dist; do
  cp $file $BUILD_DIR/etc/soccoro/`basename $file -dist`
done
popd

cp scripts/crons/socorrorc /etc/socorro/
cp scripts/init.d/socorro-${service} /etc/init.d/
cp config/crontab-dist /etc/cron.d/socorro
cp webapp-django/crashstats/settings/local.py /etc/socorro/local.py
cp config/apache.conf-dist /etc/httpd/conf.d/socorro.conf

# copy to install directory
rsync -a ${VIRTUAL_ENV} $BUILD_DIR
rsync -a socorro $BUILD_DIR/application
rsync -a scripts $BUILD_DIR/application
rsync -a tools $BUILD_DIR/application
rsync -a sql $BUILD_DIR/application
rsync -a wsgi $BUILD_DIR/application
rsync -a stackwalk $BUILD_DIR/
rsync -a scripts/stackwalk.sh $BUILD_DIR/stackwalk/bin/
rsync -a analysis $BUILD_DIR/
rsync -a alembic $BUILD_DIR/application
rsync -a webapp-django $BUILD_DIR/


# record current git revision in install dir
git rev-parse HEAD > $BUILD_DIR/application/socorro/external/postgresql/socorro_revision.txt
cp $BUILD_DIR/stackwalk/revision.txt $BUILD_DIR/application/socorro/external/postgresql/breakpad_revision.txt

# Write down build number, if ran by Jenkins
if [ -n "$BUILD_NUMBER" ]
then
  echo "$BUILD_NUMBER" > $BUILD_DIR/JENKINS_BUILD_NUMBER
fi
