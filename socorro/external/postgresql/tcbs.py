# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from datetime import datetime, timedelta
from socorro.external.postgresql.base import PostgreSQLBase

import socorro.database.database as db
import socorro.external.postgresql.tcbs_impl.classic as classic
import socorro.external.postgresql.tcbs_impl.modern as modern
import socorro.lib.external_common as external_common

logger = logging.getLogger("webapi")


def which_tcbs(db_cursor, sql_params, product, version):
    """
    Answers a boolean indicating if the old top crashes by signature should
    be used.
    """
    sql = """
                /* socorro.services.topCrashBySignatures useTCBSClassic */
                SELECT which_table
                FROM product_selector
                WHERE product_name = '%s' AND
                            version_string = '%s'""" % (product, version)
    try:
        return db.singleValueSql(db_cursor, sql, sql_params)
    except db.SQLDidNotReturnSingleValue:
        logger.info("No record in product_selector for %s %s."
            % (product, version))
        raise ValueError("No record of %s %s" % (product, version))


class TCBS(PostgreSQLBase):

    """
    Implement /topcrash/sig service with PostgreSQL.
    """

    def __init__(self, *args, **kwargs):
        super(TCBS, self).__init__(*args, **kwargs)

    def tcbs(self, **kwargs):
        """
        Return top crashers by signatures.

        See http://socorro.readthedocs.org/en/latest/middleware.html#tcbs

        Keyword arguments:

        Return:
        """
        filters = [
            ("product", None, "str"),
            ("version", None, "str"),
            ("crash_type", "all", "str"),
            ("to_date", datetime.utcnow(), "datetime"),
            ("duration", timedelta(7), "timedelta"),
            ("os", None, "str"),
            ("limit", 100, "int")
        ]

        params = external_common.parse_arguments(filters, kwargs)
        params.logger = logger
        params.productVersionCache = self.context['productVersionCache']

        try:
            connection = self.database.connection()
            cursor = connection.cursor()
            table_type = which_tcbs(cursor, {}, params.product, params.version)
            logger.debug("Using %s TCBS implementation" % table_type)
            impl = {
                "old": classic,
                "new": modern,
            }
            return impl[table_type].twoPeriodTopCrasherComparison(cursor,
                                                                  params)
        finally:
            connection.close()
