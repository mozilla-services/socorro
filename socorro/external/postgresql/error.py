# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external import MissingOrBadArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class Error(PostgreSQLBase):

    """
    Implement the /error service with PostgreSQL.
    """

    def get(self, **kwargs):
        """Return a single error report from its UUID. """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if params.uuid is None:
            raise MissingOrBadArgumentError(
                        "Mandatory parameter 'uuid' is missing or empty")

        crash_date = datetimeutil.uuid_to_date(params.uuid)
        logger.debug("Looking for error %s during day %s" % (params.uuid,
                                                             crash_date))

        sql = """/* socorro.external.postgresql.error.Error.get */
            SELECT
                bixie.crashes.signature,
                bixie.crashes.product,
                bixie.crashes.error
            FROM bixie.crashes
            WHERE bixie.crashes.crash_id=%(uuid)s
            AND bixie.crashes.success IS NOT NULL
            AND utc_day_is( bixie.crashes.processor_completed_datetime,  %(crash_date)s)
        """
        sql_params = {
            "uuid": params.uuid,
            "uuid": params.uuid,
            "crash_date": crash_date
        }

        error_message = "Failed to retrieve crash data from PostgreSQL"
        results = self.query(sql, sql_params, error_message=error_message)

        crashes = []
        for row in results:
            crash = dict(zip((
                       "product",
                       "error",
                       "signature"), row))
            crashes.append(crash)

        return {
            "hits": crashes,
            "total": len(crashes)
        }
