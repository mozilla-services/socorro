# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging

from socorro.external import MissingOrBadArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class Job(PostgreSQLBase):
    """Implement the /job service with PostgreSQL. """

    def get(self, **kwargs):
        """Return a job in the job queue. """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingOrBadArgumentError(
                        "Mandatory parameter 'uuid' is missing or empty")

        fields = [
            "id",
            "pathname",
            "uuid",
            "owner",
            "priority",
            "queueddatetime",
            "starteddatetime",
            "completeddatetime",
            "success",
            "message"
        ]
        sql = """
            /* socorro.external.postgresql.job.Job.get */
            SELECT %s FROM jobs WHERE uuid=%%(uuid)s
        """ % ", ".join(fields)

        error_message = "Failed to retrieve jobs data from PostgreSQL"
        results = self.query(sql, params, error_message=error_message)

        jobs = []
        for row in results:
            job = dict(zip(fields, row))

            # Make sure all dates are turned into strings
            for i in job:
                if isinstance(job[i], datetime.datetime):
                    job[i] = datetimeutil.date_to_string(job[i])

            jobs.append(job)

        return {
            "hits": jobs,
            "total": len(jobs)
        }
