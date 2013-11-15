# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This app tests that inserting a crash report into elasticsearch works.
It simply uses socorro.external.elasticsearch.crashstorage to send a report
and verifies that it was correctly inserted.

This app can be invoked like this:
    .../scripts/elasticsearch_backfill_app.py --help
set your path to make that simpler
set both socorro and configman in your PYTHONPATH
"""

import datetime

from configman import Namespace, converters
from isodate.isoerror import ISO8601Error

from socorro.app import generic_app
from socorro.lib import datetimeutil


class ElasticsearchBackfillApp(generic_app.App):
    app_name = 'elasticsearch_backfill'
    app_version = '0.1'
    app_description = __doc__

    required_config = Namespace()

    required_config.namespace('elasticsearch')
    required_config.elasticsearch.add_option(
        'storage_class',
        default='socorro.external.elasticsearch.crashstorage.'
                'ElasticSearchCrashStorage',
        from_string_converter=converters.class_converter,
        doc='The class to use to store crash reports in elasticsearch.'
    )
    required_config.elasticsearch.add_option(
        'elasticsearch_index_alias',
        default='socorro%Y%W_%Y%m%d',
        doc='Index to use when reindex data. Will be aliased to the regular '
            'index. '
    )

    required_config.namespace('hbase')
    required_config.hbase.add_option(
        'storage_class',
        default='socorro.external.hbase.crashstorage.HBaseCrashStorage',
        from_string_converter=converters.class_converter,
        doc='The class to use to pull crash reports from HBase.'
    )

    required_config.add_option(
        'end_date',
        default=datetimeutil.utc_now().date(),
        doc='Backfill until this date.',
        from_string_converter=converters.date_converter
    )
    required_config.add_option(
        'duration',
        default=1,
        doc='Number of weeks to backfill. '
    )
    required_config.add_option(
        'index_doc_number',
        default=100,
        doc='Number of crashes to index at a time. '
    )

    def main(self):
        self.es_storage = self.config.elasticsearch.storage_class(
            self.config.elasticsearch
        )
        self.hb_storage = self.config.hbase.storage_class(self.config.hbase)

        current_date = self.config.end_date

        one_week = datetime.timedelta(weeks=1)
        # Iterate over our indices.
        for i in range(self.config.duration):
            es_current_index = self.get_index_for_date(
                current_date,
                self.config.elasticsearch.elasticsearch_index
            )
            es_new_index = self.get_index_for_date(
                current_date,
                self.config.elasticsearch.elasticsearch_index_alias
            )

            self.config.logger.info(
                'backfilling crashes for %s',
                es_current_index
            )

            # First create the new index.
            self.es_storage.create_index(es_new_index)

            reports = self.get_reports(es_current_index, es_fields=[])
            total_num_of_crashes_in_index = reports['total']

            # Get all the reports in elasticsearch, but only a few at a time.
            for es_from in range(
                0,
                total_num_of_crashes_in_index,
                self.config.index_doc_number
            ):
                crashes_to_index = []
                reports = self.get_reports(
                    es_current_index,
                    es_from=es_from,
                    es_size=self.config.index_doc_number,
                )

                for report in reports['hits']:
                    crash_report = report['_source']
                    if 'uuid' in crash_report:
                        # This is a legacy crash report, containing only the
                        # processed crash at the root level.
                        crash_id = crash_report['uuid']
                        processed_crash = crash_report
                        raw_crash = self.hb_storage.get_raw_crash(crash_id)

                        crash_document = {
                            'crash_id': crash_id,
                            'processed_crash': processed_crash,
                            'raw_crash': raw_crash,
                        }
                    elif 'processed_crash' in crash_report:
                        # This is a new style crash report, with branches for
                        # the processed crash and the raw crash.
                        crash_document = crash_report
                    else:
                        raise KeyError('''Unable to understand what type of
                            document was retrieved from elasticsearch''')

                    crashes_to_index.append(crash_document)

                self.index_crashes(es_new_index, crash_document)

            # Now that reindexing is done, delete the old index and
            # create an alias to the new one.
            self.es_storage.es.delete_index(es_current_index)
            self.es_storage.es.update_aliases({
                'actions': [
                    {
                        'add': {
                            'index': es_new_index,
                            'alias': es_current_index,
                        }
                    }
                ]
            })

            current_date -= one_week

        return 0

    def get_reports(self, index, es_fields=None, es_size=0, es_from=0):
        """Return some reports from an elasticsearch index. """
        es_query = {
            'query': {
                'match_all': {}
            },
            'fields': es_fields,
            'size': es_size,
            'from': es_from
        }
        return self.es_storage.es.search(
            es_query,
            index=index,
        )['hits']

    def get_index_for_date(self, date, index_format):
        """return the elasticsearch index for a date"""
        if not index_format:
            return None

        if '%' in index_format:
            return date.strftime(index_format)

        return index_format

    def format_dates_in_crash(self, processed_crash):
        # HBase returns dates in a format that elasticsearch does not
        # understand. To keep our elasticsearch mapping simple, we
        # transform all dates to a recognized format.
        for attr in processed_crash:
            try:
                processed_crash[attr] = datetimeutil.date_to_string(
                    datetimeutil.string_to_datetime(
                        processed_crash[attr]
                    )
                )
            except (ValueError, TypeError, ISO8601Error):
                # the attribute is not a date
                pass

        return processed_crash

    def index_crashes(self, es_index, crashes_to_index):
        self.es_storage.es.bulk_index(
            es_index,
            self.config.elasticsearch.elasticsearch_doctype,
            crashes_to_index,
            id_field='crash_id'
        )


if __name__ == '__main__':
    generic_app.main(ElasticsearchBackfillApp)
