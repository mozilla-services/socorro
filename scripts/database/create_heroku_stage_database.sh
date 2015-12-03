#!/usr/bin/env bash

# This script destroys and then creates a Heroku stage database
# from a minimal set of tables drawn from our PHX1 stage database.

# To use:
#
# 1. Run this script as the 'postgres' user on PHX1 stage
# 2. Export PGPASSWORD and HEROKU_STAGE_APP
# 3. Set up ~/.netrc

set -e
set -u

###############################################################################
# BEGIN CONFIG
###############################################################################
VENV="${VIRTUAL_ENV:-/data/socorro/socorro-virtualenv}"
PYTHON="${VIRTUAL_ENV}/bin/python"

# Local files
SLIM_DUMP=slim_socorro_db.dump
FULL_DUMP=full_socorro_db.dump

# Databases
SOURCE_DATABASE=${database:-'breakpad'}
TEMP_DATABASE=${temp_database:-'socorro_stage_temp'}

# Heroku toolbelt can output STDERR
HEROKU_STAGE_APP="${heroku_stage_app}"
HEROKU_STAGE_DB_URL="$(heroku config:get DATABASE_URL -a ${HEROKU_STAGE_APP} 2>/dev/null)"

STAGE_PASSWORD="${PGPASSWORD:-}"

export PGUSER=${PGUSER:-'postgres'}
PSQL="psql -U ${PGUSER}"

# Set production deploy directory
APPLICATION_DIR=${application_dir:-'/data/socorro/application'}

# Set up some helper variables like $PYTHON
if [ -e /etc/socorro/socorrorc ]
then
    source /etc/socorro/socorrorc
fi

# Enable access to installed prod python modules
if [ -z ${VIRTUAL_ENV} ]
then
    source ${VENV}/bin/activate
fi

###############################################################################
# END CONFIG
###############################################################################

function log() {
    message=$1$
    echo -n `date`
    echo " ${message}"
}

###############################################################################
# ERROR HANDLING
###############################################################################
function cleanup() {
    echo "INFO: Removing backup files"
    rm "${SLIM_DUMP}" "${FULL_DUMP}"

    echo "INFO: cleaning up temp database"
    $PSQL $PGUSER -c "DROP DATABASE ${TEMP_DATABASE}"

    exit
}

trap 'cleanup' INT TERM
###############################################################################
# END ERROR HANDLING
###############################################################################

log "INFO: Using database ${SOURCE_DATABASE}: writing a slim pg dump to ${SLIM_DUMP}"
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


# Move directories so that we get the alembic environment configuration
pushd ${APPLICATION_DIR}

log "INFO: Setting up a local temp database: ${TEMP_DATABASE}"
# Setup a fresh database from our repo
# The hostname is set to '' so that psycopg2 uses a local socket, thereby avoiding ACLs
$PYTHON ${VENV}/bin/socorro setupdb \
    --database_name=${TEMP_DATABASE} \
    --no_staticdata \
    --dropdb \
    --no_roles \
    --database_hostname='' \
    --database_superusername=$PGUSER \
    --database_superuserpassword="${STAGE_PASSWORD}" \
    --database_username=$PGUSER \
    --database_password="${STAGE_PASSWORD}"
popd

log "INFO: Removing old ADI to speed up restore"
# Remove old ADI to help make restore time finite
$PSQL ${TEMP_DATABASE} -c "DELETE FROM raw_adi where date < now() - '7 days'::interval"
$PSQL ${TEMP_DATABASE} -c "DELETE FROM raw_adi_logs where report_date < now() - '7 days'::interval"

log "INFO: Creating a full dump of ${TEMP_DATABASE} for restore into Heroku into file ${FULL_DUMP}"
# Do a full dump
pg_dump \
    ${TEMP_DATABASE} \
    -U $PGUSER \
    -F c \
    --no-owner \
    --no-acl \
    -v \
    -f ${FULL_DUMP}

log "INFO: Resetting Heroku database for app: ${HEROKU_STAGE_APP}"
# Reset our stage database
heroku pg:reset DATABASE_URL --confirm ${HEROKU_STAGE_APP}

log "INFO: Restoring full dump into Heroku using HEROKU_STAGE_DB_URL"
# Restore to heroku
pg_restore \
    -d ${HEROKU_STAGE_DB_URL} \
    --no-owner \
    --no-acl \
    -v \
    ${FULL_DUMP}

log "INFO: Cleaning up"
# Cleanup our temp database and backup files
cleanup
