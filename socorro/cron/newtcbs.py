#!/usr/bin/env python

import sys
import logging
import datetime
import psycopg2

logger = logging.getLogger('newtcbs')
logger.addHandler(logging.StreamHandler(sys.stderr))


def update(config, targetDate):
    functions = (
      # function name, parmeters, dependencies
      ('update_product_versions', [], []),
      ('update_signatures', [targetDate], []),
      ('update_os_versions', [targetDate], []),
      ('update_tcbs', [targetDate],
       ['update_product_versions', 'update_signatures', 'update_os_versions']),
      ('update_adu', [targetDate], []),
      ('update_daily_crashes', [targetDate],
       ['update_product_versions' 'update_signatures']),
      ('update_os_signature_counts', [targetDate], []),
      ('update_uptime_signature_counts', [targetDate], []),
      ('update_product_signature_counts', [targetDate], []),
    )

    failed = set()
    databaseDSN = ""
    if 'databaseHost' in config:
        databaseDSN += 'host=%(databaseHost)s '
    if 'databaseName' in config:
        databaseDSN += 'dbname=%(databaseName)s '
    if 'databaseUserName' in config:
        databaseDSN += 'user=%(databaseUserName)s '
    if 'databasePassword' in config:
        databaseDSN += 'password=%(databasePassword)s'
    dsn = databaseDSN % config
    connection = psycopg2.connect(dsn)
    cursor = connection.cursor()
    for funcname, parameters, deps in functions:
        if set(deps) & failed:
            # one of the deps previously failed, so skip this one
            logger.warn("For %r, dependency %s failed so skipping"
                         % (funcname, ', '.join(set(deps) & failed)))
            continue
        logger.info('Running %s' % funcname)
        failureMessage = None
        success = False
        try:
            cursor.callproc(funcname, parameters)
            # fetchone() returns a tuple of length 1
            result = cursor.fetchone()
            if result and result[0]:
                success = True
            else:
                # "expected" error
                logger.warn('%r failed' % funcname)
                failureMessage = '%s did not return true' % funcname
        except psycopg2.InternalError:
            # unexpected error
            logger.error('%r failed' % funcname, exc_info=True)
            import sys  # don't assume that this has been imported
            __, error_value = sys.exc_info()[:2]
            failureMessage = str(error_value)
        if success:
            connection.commit()
        else:
            connection.rollback()
            failed.add(funcname)
        updateCronjobsTable(connection, 'newtcbs:%s' % funcname,
                            success, targetDate,
                            failureMessage=failureMessage)

    return len(failed)


def updateCronjobsTable(connection, cronjobName, success, lastTargetTime,
                        failureMessage=None):
    cursor = connection.cursor()

    params = [lastTargetTime]
    if success:
        params.append(datetime.datetime.utcnow())
        sql = """
          /* socorro.cron.newtcbs updateCronjobsTable */
          UPDATE cronjobs
          SET
            last_target_time = %s,
            last_success = %s
          WHERE cronjob = %s
        """
    else:
        params.append(datetime.datetime.utcnow())
        params.append(failureMessage)
        sql = """
          /* socorro.cron.newtcbs updateCronjobsTable */
          UPDATE cronjobs
          SET
            last_target_time = %s,
            last_failure = %s,
            failure_message = %s
          WHERE cronjob = %s
        """
    params.append(cronjobName)

    cursor.execute(sql, params)
    connection.commit()
