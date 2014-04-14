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
                 beta_number, repository, version_build=None,
                 ignore_duplicates=False):
    """ Insert a particular build into the database """
    # As we use beta numbers, we don't want to keep the 'bX' in versions
    if "b" in version:
        version = version[:version.index("b")]

    if beta_number is not None:
        beta_number = int(beta_number)

    params = {
        "product": str(product_name),
        "version": version,
        "build_type": build_type,
        "build_id": int(build_id),
        "platform": platform,
        "beta_number": beta_number,
        "repository": repository,
        "version_build": version_build,
        "ignore_duplicates": ignore_duplicates
    }

    logger.info("Trying to insert new release: %s" % str(params))

    sql = """/* socorro.lib.buildutil.insert_build */
        SELECT add_new_release(
            %(product)s,
            %(version)s,
            %(build_type)s,
            %(build_id)s,
            %(platform)s,
            %(beta_number)s,
            %(repository)s,
            %(version_build)s,
            true,
            %(ignore_duplicates)s
        )
    """

    try:
        cursor.execute(sql, params)
        cursor.connection.commit()
    except psycopg2.Error, e:
        cursor.connection.rollback()
        logger.error("Failed inserting new release: %s" % e)
        raise
