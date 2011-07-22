#!/usr/bin/python
"""
Code behind startDailyCrash.py
"""

import datetime as datetime

import socorro.database.adu_codes as adu_codes
import socorro.database.database as db
import socorro.lib.util as util


#-----------------------------------------------------------------------------------------------------------------
def most_recent_day(databaseCursor, logger):
  """ Determines the last time we ran using the
      daily_crash or product_visibility tables. If all else fails
      it will return the current day.
      """
  try:
    day = db.singleValueSql(databaseCursor, "SELECT MAX(adu_day) FROM daily_crashes")
    if day:
      return day + datetime.timedelta(days=1)
    logger.info("daily_crashes was empty, using product_visibility to determine start date")
  except Exception:
    util.reportExceptionAndContinue(logger)
    databaseCursor.connection.rollback()
    logger.warning("Ouch, db error accessing daily_crashes, using product_visibility to determine start date")
  try:
    day = most_recent_day_from_product_visibility(databaseCursor, logger)
    if day:
      return day
    else:
      return fail_most_recent_day(logger)
  except Exception:
    util.reportExceptionAndContinue(logger)
    databaseCursor.connection.rollback()
    return fail_most_recent_day(logger)

#-----------------------------------------------------------------------------------------------------------------
def most_recent_day_from_product_visibility(databaseCursor, logger):
  """ Corner case, first run for dail_crash, so we use the
      oldest date where we will want to report on daily crashes """
  return db.singleValueSql(databaseCursor, "SELECT MIN(start_date) FROM product_visibility")

#-----------------------------------------------------------------------------------------------------------------
def fail_most_recent_day(logger):
  """ Corner case, no useful dates... fresh install?
      Returns the current date """
  logger.error("Unable to determine where to start. daily_crashes and product_visibility are empty.")
  return datetime.date.today() - datetime.timedelta(7)

insert_crashes_sql = """
  INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
    -- for CRASH_BROWSER
      SELECT COUNT(r.uuid) as count, %s, p.id, substring(r.os_name, 1, 3) AS os_short_name,
             timestamp without time zone %s
      FROM product_visibility cfg
      JOIN productdims p on cfg.productdims_id = p.id
      JOIN reports r on p.product = r.product AND p.version = r.version
      WHERE NOT cfg.ignore AND
            timestamp without time zone %s - interval %s <= r.date_processed AND
            r.date_processed < timestamp without time zone %s + (interval '24 hours' - interval %s) AND
            cfg.start_date <= r.date_processed AND r.date_processed <= cfg.end_date AND
            hangid IS NULL and process_type IS NULL
      GROUP BY p.id, os_short_name
    UNION
    -- for OOP_PLUGIN
      SELECT count(uuid) as count, %s, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name,
             timestamp without time zone %s
      FROM product_visibility cfg
      JOIN productdims p on cfg.productdims_id = p.id
      JOIN reports r on p.product = r.product AND p.version = r.version
      WHERE NOT cfg.ignore AND
          timestamp without time zone %s - interval %s <= r.date_processed AND
          r.date_processed < timestamp without time zone %s + (interval '24 hours' - interval %s) AND
          cfg.start_date <= r.date_processed AND r.date_processed <= cfg.end_date AND
          hangid IS NULL AND process_type = 'plugin'
      GROUP BY prod_id, os_short_name
    UNION
    -- for HANGS_NORMALIZED
      SELECT count(subr.hangid) as count, %s, subr.prod_id, subr.os_short_name,
             timestamp without time zone %s
      FROM (
                   SELECT distinct hangid, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name
                   FROM product_visibility cfg
                   JOIN productdims p on cfg.productdims_id = p.id
                   JOIN reports r on p.product = r.product AND p.version = r.version
                   WHERE NOT cfg.ignore AND
                         timestamp without time zone %s - interval %s <= r.date_processed AND
                         r.date_processed < timestamp without time zone %s + (interval '24 hours' - interval %s) AND
                         cfg.start_date <= r.date_processed AND r.date_processed <= cfg.end_date AND
                         hangid IS NOT NULL
                 ) AS subr
             GROUP BY subr.prod_id, subr.os_short_name
    UNION
    -- for HANG_PLUGIN
      SELECT count(uuid) as count, %s, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name,
             timestamp without time zone %s
      FROM product_visibility cfg
      JOIN productdims p on cfg.productdims_id = p.id
      JOIN reports r on p.product = r.product AND p.version = r.version
      WHERE NOT cfg.ignore AND
          timestamp without time zone %s - interval %s <= r.date_processed AND
          r.date_processed < timestamp without time zone %s + (interval '24 hours' - interval %s) AND
          cfg.start_date <= r.date_processed AND r.date_processed <= cfg.end_date AND
          hangid IS NOT NULL AND process_type = 'plugin'
      GROUP BY prod_id, os_short_name
    UNION
    -- for HANG_BROWSER
      SELECT count(uuid) as count, %s, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name,
             timestamp without time zone %s
      FROM product_visibility cfg
      JOIN productdims p on cfg.productdims_id = p.id
      JOIN reports r on p.product = r.product AND p.version = r.version
      WHERE NOT cfg.ignore AND
          timestamp without time zone %s - interval %s <= r.date_processed AND
          r.date_processed < timestamp without time zone %s + (interval '24 hours' - interval %s) AND
          cfg.start_date <= r.date_processed AND r.date_processed <= cfg.end_date AND
          hangid IS NOT NULL AND process_type IS NULL
      GROUP BY prod_id, os_short_name
    UNION
    -- for CONTENT
      SELECT count(uuid) as count, %s, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name,
             timestamp without time zone %s
      FROM product_visibility cfg
      JOIN productdims p on cfg.productdims_id = p.id
      JOIN reports r on p.product = r.product AND p.version = r.version
      WHERE NOT cfg.ignore AND
          timestamp without time zone %s - interval %s <= r.date_processed AND
          r.date_processed < timestamp without time zone %s + (interval '24 hours' - interval %s) AND
          cfg.start_date <= r.date_processed AND r.date_processed <= cfg.end_date AND
          process_type = 'content'
      GROUP BY prod_id, os_short_name
      """


def continue_aggregating(previousDay, today):
  return previousDay.date() < today.date()

#-----------------------------------------------------------------------------------------------------------------
def record_crash_stats(config, logger):
  database = db.Database(config)
  databaseConnection = database.connection()
  try:
    databaseCursor = databaseConnection.cursor()
    today = datetime.datetime.today()
    one_day = datetime.timedelta(days=1)

    previousDay = most_recent_day(databaseCursor, logger) # + one_day

    logger.info("Beginning search from this date (YYYY-MM-DD): %s", previousDay)
    while continue_aggregating(previousDay, today):
      # This should be zero hour if pulled from daily_crashes or product_visibility, but make sure
      previousZeroHour = datetime.datetime(previousDay.year, previousDay.month, previousDay.day)
      socorroTimeToUTCInterval = config.socorroTimeToUTCInterval
      parameters = (adu_codes.CRASH_BROWSER,     previousDay.date(), previousZeroHour, socorroTimeToUTCInterval, previousZeroHour, socorroTimeToUTCInterval,
                    adu_codes.OOP_PLUGIN,        previousDay.date(), previousZeroHour, socorroTimeToUTCInterval, previousZeroHour, socorroTimeToUTCInterval,
                    adu_codes.HANGS_NORMALIZED,  previousDay.date(), previousZeroHour, socorroTimeToUTCInterval, previousZeroHour, socorroTimeToUTCInterval,
                    adu_codes.HANG_PLUGIN,       previousDay.date(), previousZeroHour, socorroTimeToUTCInterval, previousZeroHour, socorroTimeToUTCInterval,
                    adu_codes.HANG_BROWSER,      previousDay.date(), previousZeroHour, socorroTimeToUTCInterval, previousZeroHour, socorroTimeToUTCInterval,
                    adu_codes.CONTENT,           previousDay.date(), previousZeroHour, socorroTimeToUTCInterval, previousZeroHour, socorroTimeToUTCInterval,
                   )
      try:
        logger.debug("Processing %s crashes for use with ADU data" % previousDay)
        #logger.debug(databaseCursor.mogrify(insert_crashes_sql.encode(databaseCursor.connection.encoding), parameters))
        databaseCursor.execute(insert_crashes_sql, parameters)
        logger.info("Inserted %d rows" % databaseCursor.rowcount)
        databaseCursor.connection.commit()
      except Exception:
        util.reportExceptionAndContinue(logger)
        databaseCursor.connection.rollback()
      logger.debug("Finished %s" % previousDay)
      previousDay = previousDay + one_day
  finally:
    databaseConnection.close()

