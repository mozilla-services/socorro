# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from configman import Namespace
from crontabber.base import BaseCronApp
from crontabber.mixins import (
    as_backfill_cron_app,
    with_postgres_transactions
)

from socorro.external.postgresql.signature_first_date import SignatureFirstDate
from socorro.external.es.base import ElasticsearchConfig
from socorro.external.es.supersearch import SuperSearch
from socorro.external.es.super_search_fields import SuperSearchFields


# Maximum number of results returned for a super search query
MAX_PAGE = 1000


@with_postgres_transactions()
@as_backfill_cron_app
class UpdateSignaturesCronApp(BaseCronApp):
    """Updates the signatures table using crash data from Elasticsearch"""
    app_name = 'update-signatures'
    app_description = 'Updates signatures table'
    app_version = '0.1'

    required_config = Namespace()
    # NOTE(willkg): period defaults to 90 minutes because this job runs hourly
    # and that creates some overlap with the previous period even if this run
    # and the last run didn't run on the hour.
    required_config.add_option(
        'period',
        default=90,
        doc='Length of the window to look at in minutes'
    )
    required_config.add_option(
        'elasticsearch_class',
        default=ElasticsearchConfig,
    )
    required_config.add_option(
        'dry_run',
        default=False,
        doc='Print to stdout instead of updating/inserting data'
    )

    def run(self, end_datetime):
        # Truncate to the hour
        end_datetime = end_datetime.replace(minute=0, second=0, microsecond=0)

        # Do a super search and get the signature, buildid, and date processed for
        # every crash in the range
        all_fields = SuperSearchFields(config=self.config).get()
        api = SuperSearch(config=self.config)
        start_datetime = end_datetime - datetime.timedelta(minutes=self.config.period)
        self.config.logger.info('Looking at %s to %s', start_datetime, end_datetime)

        params = {
            'date': [
                '>={}'.format(start_datetime.isoformat()),
                '<{}'.format(end_datetime.isoformat()),
            ],
            '_columns': ['signature', 'build_id', 'date'],
            '_facets_size': 0,
            '_fields': all_fields,

            # Set up first page
            '_results_offset': 0,
            '_results_number': MAX_PAGE,
        }

        results = {}
        crashids_count = 0

        while True:
            resp = api.get(**params)
            hits = resp['hits']
            for hit in hits:
                crashids_count += 1

                if not hit['build_id']:
                    # Not all crashes have a build id, so skip the ones that don't.
                    continue

                if hit['signature'] in results:
                    data = results[hit['signature']]
                    data['build_id'] = min(data['build_id'], hit['build_id'])
                    data['date'] = min(data['date'], hit['date'])
                else:
                    data = {
                        'signature': hit['signature'],
                        'build_id': hit['build_id'],
                        'date': hit['date']
                    }
                results[hit['signature']] = data

            # If there are no more crash ids to get, we return
            total = resp['total']
            if not hits or crashids_count >= total:
                break

            # Get the next page, but only as many results as we need
            params['_results_offset'] += MAX_PAGE
            params['_results_number'] = min(
                # MAX_PAGE is the maximum we can request
                MAX_PAGE,

                # The number of results Super Search can return to us that is hasn't returned so far
                total - crashids_count
            )

        signature_data = results.values()

        # Save signature data to the db
        signature_first_date_api = SignatureFirstDate(config=self.config)
        for item in signature_data:
            if self.config.dry_run:
                self.config.logger.info(
                    'Inserting/updating signature (%s, %s, %s)',
                    item['signature'],
                    item['date'],
                    item['build_id']
                )
            else:
                signature_first_date_api.post(
                    signature=item['signature'],
                    first_report=item['date'],
                    first_build=item['build_id']
                )

        self.config.logger.info('Inserted/updated %d signatures.', len(signature_data))
