# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external import MissingOrBadArgumentError
from socorro.lib import external_common


BACKFILL_PARAMETERS = {
    "adu": ['update_day'],
    "all_dups": ['start_date', 'end_date'],
    "build_adu": ['update_day'],
    "correlations": ['update_day'],
    "crashes_by_user_build": ['update_day', 'check_period'],
    "crashes_by_user": ['update_day', 'check_period'],
    "daily_crashes": ['update_day'],
    "exploitability": ['update_day'],
    "explosiveness": ['update_day'],
    "hang_report": ['update_day'],
    "home_page_graph_build": ['update_day', 'check_period'],
    "home_page_graph": ['update_day', 'check_period'],
    "matviews": ['start_date', 'end_date', 'reports_clean', 'check_period'],
    "nightly_builds": ['update_day'],
    "one_day": ['update_day'],
    "rank_compare": ['update_day'],
    "reports_clean": ['start_date', 'end_date'],
    "reports_duplicates": ['start_date', 'end_date'],
    "signature_counts": ['start_date', 'end_date'],
    "signature_summary": ['update_day'],
    "tcbs_build": ['update_day', 'check_period'],
    "tcbs": ['update_day', 'check_period'],
    "weekly_report_partitions": ['start_date', 'end_date', 'table_name']
}


class Backfill(PostgreSQLBase):

    def get(self, **kwargs):

        filters = [
            ("backfill_type", None, "str"),
            ("reports_clean", True, "bool"),
            ("check_period", '01:00:00', "str"),
            ("table_name", None, "str"),
            ("update_day", None, "datetime"),
            ("start_date", None, "datetime"),
            ("end_date", None, "datetime"),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        if not params.backfill_type:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'backfill_type' is missing or empty"
            )

        date_param = ['update_day', 'start_date', 'end_date']
        for i in date_param:
            if i in kwargs:
                params[i] = str(params[i].date())

        try:
            query = 'SELECT backfill_%(backfill_type)s (%(params)s); '
            required_params = BACKFILL_PARAMETERS[params.backfill_type]
            query_params = [(i, params[i]) for i in required_params]
            query_params_str = ', '.join(
                '%(' + str(i[0]) + ')s' for i in query_params
            )
            query = query % {'backfill_type': params.backfill_type,
                             'params': query_params_str}
            print query % params
        except:
            raise MissingOrBadArgumentError(
                "Couldn't catch the right parameters for backfill %s"
                % kwargs['backfill_type']
            )

        error_message = "Failed to retrieve backfill %s from PostgreSQL"
        error_message = error_message % kwargs['backfill_type']
        results = self.query(query, params, error_message=error_message)
        return results
