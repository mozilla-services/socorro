# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
buildutil.py provides utility functions for querying, editing, and adding
builds to Socorro.
"""
import logging
import psycopg2

logger = logging.getLogger("webapi")


def insert_build(cursor, product_name, version, platform, build_id, build_type,
                 beta_number, repository):
    """ Insert a particular build into the database """
    # As we use beta numbers, we don't want to keep the 'bX' in versions
    if "b" in version:
        version = version[:version.index("b")]

    if beta_number is not None:
        beta_number = int(beta_number)

    params = (str(product_name), version, build_type, int(build_id),
              platform, beta_number, repository)

    logger.info("Trying to insert new release: %s %s %s %s %s %s %s" % params)

    sql = """/* socorro.lib.buildutil.insert_build */
        SELECT add_new_release(%s, %s, %s, %s, %s, %s, %s)
    """

    try:
        cursor.execute(sql, params)
        cursor.connection.commit()
    except psycopg2.Error, e:
        cursor.connection.rollback()
        logger.error("Failed inserting new release: %s" % e,
                     exc_info=True)
        raise
