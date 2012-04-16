"""
buildutil.py provides utility functions for querying, editing, and adding
builds to Socorro.
"""
import logging

import util

logger = logging.getLogger("webapi")

def build_exists(cursor, product_name, version, platform, build_id, build_type,
                beta_number, repository):
    """ Determine whether or not a particular release build exists already """
    sql = """
        SELECT *
        FROM releases_raw
        WHERE product_name = %s
        AND version = %s
        AND platform = %s
        AND build_id = %s
        AND build_type = %s
    """

    if beta_number is not None:
        sql += """ AND beta_number = %s """
    else:
        sql += """ AND beta_number IS %s """

    sql += """ AND repository = %s """

    params = (product_name, version, platform, build_id, build_type,
              beta_number, repository)
    cursor.execute(sql, params)
    exists = cursor.fetchone()

    return exists is not None


def insert_build(cursor, product_name, version, platform, build_id, build_type,
                beta_number, repository):
    """ Insert a particular build into the database """
    if not build_exists(cursor, product_name, version, platform, build_id,
                       build_type, beta_number, repository):
        sql = """ INSERT INTO releases_raw
                  (product_name, version, platform, build_id, build_type,
                   beta_number, repository)
                  VALUES (%s, %s, %s, %s, %s, %s, %s)"""

        try:
            params = (product_name, version, platform, build_id, build_type,
                      beta_number, repository)
            cursor.execute(sql, params)
            cursor.connection.commit()
            logger.info("Inserted: %s %s %s %s %s %s %s" % params)
        except Exception:
            cursor.connection.rollback()
            util.reportExceptionAndAbort(logger)
