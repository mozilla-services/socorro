#!/usr/bin/env bash

# This script destroys and then creates a Heroku stage database 
# from a minimal set of tables drawn from our PHX1 stage database.

# To use:
#
# 1. Run this script as the 'postgres' user on PHX1 stage
# 2. Export PGPASSWORD and HEROKU_STAGE_APP
# 3. Set up ~/.netrc 
#

###############################################################################
# BEGIN CONFIG
###############################################################################
VENV=/data/socorro/socorro-virtualenv

# Local files
SLIM_DUMP=slim_socorro_db.dump
FULL_DUMP=full_socorro_db.dump

# Databases 
SOURCE_DATABASE=${database:-'breakpad'}
TEMP_DATABASE=${temp_database:-'socorro_stage_temp'}

# Heroku toolbelt can output STDERR
HEROKU_STAGE_APP=${heroku_stage_app}
HEROKU_STAGE_DB_URL="$(heroku config:get DATABASE_URL -a ${HEROKU_STAGE_APP} 2>/dev/null)"

STAGE_PASSWORD=${PGPASSWORD:-}

PSQL="psql -U postgres"

export PGUSER=postgres 

# Set up some helper variables like $PYTHON
source /etc/socorro/socorrorc

# Enable access to installed prod python modules
source ${VENV}/bin/activate

###############################################################################
# END CONFIG
###############################################################################

echo date
# make a slim dump
pg_dump \
        -a \
        -t android_devices \
        -t build_adu \
        -t crash_types \
        -t data_dictionary \
        -t os_name_matches \
        -t os_names \
        -t os_versions \
        -t process_types \
        -t product_build_types \
        -t product_productid_map \
        -t product_release_channels \
        -t product_versions \
        -t products \
        -t raw_adi  \
        -t raw_adi_logs \
        -t raw_update_channels \
        -t reasons  \
        -t release_channel_matches \
        -t release_channels \
        -t release_repositories \
        -t releases_raw  \
        -t report_partition_info \
        -t signature_products \
        -t signature_products_rollup \
        -t signatures \
        -t skiplist \
        -t special_product_platforms \
        -t suspicious_crash_signatures \
        -t transform_rules \
        -t update_channel_map \
        -t uptime_levels \
        -t windows_versions \
        -F c \
        --no-acl --no-owner \
        --disable-triggers \
        -v \
        -f ${SLIM_DUMP} \
        ${SOURCE_DATABASE}

echo date 

# Move directories so that we get the alembic environment configuration
pushd /data/socorro/application
# Setup a fresh database from our repo
# The hostname is set to '' so that psycopg2 uses a local socket, thereby avoiding ACLs
$PYTHON ${VENV}/bin/socorro setupdb --database_name=${TEMP_DATABASE} --no_staticdata --dropdb --no_roles\
	--database_hostname='' \
	--database_superusername=postgres --database_superuserpassword="${STAGE_PASSWORD}" \
	--database_username=postgres --database_password="${STAGE_PASSWORD}"
popd

echo date

# Remove old ADI to help make restore time finite
$PSQL ${TEMP_DATABASE} -c "DELETE FROM raw_adi where date < now() - '7 days'::interval" 
$PSQL ${TEMP_DATABASE} -c "DELETE FROM raw_adi_logs where report_date < now() - '7 days'::interval"

# Do a full dump
pg_dump -U postgres ${TEMP_DATABASE} -F c --no-owner --no-acl -v -f ${FULL_DUMP}

# Reset our stage database
heroku pg:reset ${HEROKU_STAGE_APP} --confirm ${HEROKU_STAGE_APP}

# Restore to heroku
pg_restore --no-owner --no-acl -v -d ${HEROKU_STAGE_DB_URL} ${FULL_DUMP}

# Cleanup our temp database
$PSQL postgres -c "DROP DATABASE ${TEMP_DATABASE}"


