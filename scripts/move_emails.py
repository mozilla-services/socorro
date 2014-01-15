# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Move emails data from PostgreSQL to elasticsearch.

This is a one time use script that is needed for bug 931907 - changing the
automatic-emails cron job to use elasticsearch means that we need to move
all data about the emails that we previously sent into elasticsearch, to avoid
sending the same email twice.
"""

import datetime

from configman import Namespace
from configman.converters import class_converter

from socorro.app import generic_app
from socorro.lib import datetimeutil


class MoveEmailsApp(generic_app.App):
    """Move emails data from PostgreSQL to elasticsearch. """

    app_name = 'move-emails'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()

    required_config.namespace('elasticsearch')
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.elasticsearch.connection_context.'
                'ConnectionContext',
        from_string_converter=class_converter
    )
    required_config.elasticsearch.add_option(
        'index_creator_class',
        default='socorro.external.elasticsearch.crashstorage.'
                'ElasticSearchCrashStorage',
        from_string_converter=class_converter
    )

    required_config.namespace('database')
    required_config.database.add_option(
        'database_class',
        default='socorro.external.postgresql.connection_context.'
                'ConnectionContext',
        from_string_converter=class_converter
    )

    def main(self):
        start_date = datetimeutil.utc_now() - datetime.timedelta(weeks=1)

        # Create the emails index in elasticsearch.
        index_creator = self.config.elasticsearch.index_creator_class(
            self.config.elasticsearch
        )
        index_creator.create_emails_index()

        es_connection = index_creator.es

        # Create connection to PostgreSQL.
        pg_context = self.config.database.database_class(self.config.database)

        # Get data from PostgreSQL.
        with pg_context() as pg_connection:
            cursor = pg_connection.cursor()

            sql = """
                SELECT email, last_sending
                FROM emails
                WHERE last_sending >= %s
            """
            cursor.execute(sql, (start_date,))
            results = cursor.fetchall()
            if not results:
                self.config.logger.info('No data in emails table in postgres')
                return

            for row in results:
                # self.config.logger.info('putting %s into ES' % row[0])
                if not row[0] or not row[0].strip():
                    continue

                es_connection.index(
                    index=self.config.elasticsearch.elasticsearch_emails_index,
                    doc_type='emails',
                    doc={
                        'last_sending': row[1]
                    },
                    id=row[0]
                )


if __name__ == '__main__':
    generic_app.main(MoveEmailsApp)
