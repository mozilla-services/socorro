import datetime
import sys

import mock

from configman import Namespace
from configman.converters import class_converter
from crontabber.base import BaseCronApp
from crontabber.mixins import (
    as_backfill_cron_app,
    with_postgres_transactions
)

from socorro.external.postgresql.signature_first_date import SignatureFirstDate
from socorro.external.es.base import ElasticsearchConfig
from socorro.external.es.supersearch import SuperSearch
from socorro.external.es.super_search_fields import SuperSearchFields
from socorro.app.socorro_app import App, main
from socorro.lib.datetimeutil import string_to_datetime


class SuperSearchErrors(Exception):
    """Happens when we make a SuperSearch query and there's something in the
    results 'errors' dict."""


@with_postgres_transactions()
@as_backfill_cron_app
class FirstSignaturesCronApp(BaseCronApp):
    app_name = 'first-signatures'
    app_description = 'Using SuperSearch to log when signatures first appeared'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'window_seconds',
        default=60 * 60,  # seconds
        doc='Number of seconds to search for signature facets back'
    )
    required_config.add_option(
        'sensitive_to_errors',
        # default=True,
        default=False,
        doc=(
            'If there are, for example, missing indexes in ES you can get errors '
            "in supersearch doing queries across dates we don't have indices for. "
            'If this is the case, halt this crontabber app.'
        )
    )
    required_config.add_option(
        'historic_days',
        # The number 26 comes from the default in index_cleaner which is used
        # as a retention policy for cleaning elasticsearch.
        default=26 * 7,  # days
        doc=(
            'When looking for the oldest crash possible (by a specific signature) '
            'go back this many days'
        )
    )
    required_config.add_option(
        'elasticsearch_class',
        default=ElasticsearchConfig,
    )

    def run(self, date):
        # First get a list of all unique signatures, in the given timespan
        all_fields = SuperSearchFields(config=self.config).get()
        api = SuperSearch(config=self.config)
        assert isinstance(date, datetime.datetime), type(date)
        start_date = date - datetime.timedelta(seconds=self.config.window_seconds)
        params = {
            'date': [
                '>={}'.format(start_date.isoformat()),
                '<{}'.format(date.isoformat()),
            ],
            '_facets': 'signature',
            '_facets_size': 1000,
            '_results_number': 0,
            '_fields': all_fields,
        }
        results = api.get(**params)
        signatures = [
            x['term'] for x in results['facets']['signature']
        ]
        self.config.logger.info(
            'Found %s unique signatures between %s and %s',
            len(signatures),
            start_date,
            date,
        )
        if not signatures:
            self.config.logger.info(
                'Exit early because no signature facets'
            )
            return

        # Now to figure out which ones we've never seen before
        signature_first_date_api = SignatureFirstDate(config=self.config)
        results = signature_first_date_api.get(signatures=signatures)
        new_signatures = set(signatures) - set(results['hits'])
        self.config.logger.info('%s new signatures', len(new_signatures))

        for signature in new_signatures:
            # First look up by the oldest 'date'.
            params = {
                '_results_number': 1,
                'signature': '={}'.format(signature),
                '_sort': 'date',
                '_fields': all_fields,
                '_columns': ['date'],
                '_facets_size': 0,
                'date': [
                    '>={}'.format(start_date.isoformat()),
                    '<{}'.format(date.isoformat()),
                ],
            }
            results = api.get(**params)
            if results['errors'] and self.config.sensitive_to_errors:
                raise SuperSearchErrors(results['errors'])
            first_crash_date = string_to_datetime(results['hits'][0]['date'])

            # Now, same procedure by sorted by oldest 'build_id'
            params['_sort'] = 'build_id'
            params['_columns'] = 'build_id'
            results = api.get(**params)
            if results['errors'] and self.config.sensitive_to_errors:
                raise SuperSearchErrors(results['errors'])
            first_crash_build_id = results['hits'][0]['build_id']

            # Finally we can insert this
            signature_first_date_api.post(
                signature=signature,
                first_report=first_crash_date,
                first_build=first_crash_build_id,
            )
            self.config.logger.info(
                'Inserting first signature %r (%s, %s)',
                signature,
                first_crash_date,
                first_crash_build_id,
            )


class FirstSignaturesCronAppDryRunner(App):  # pragma: no cover
    """This is a utility class that makes it easy to run the scraping
    and ALWAYS do so in a "dry run" fashion such that stuff is never
    stored in the database but instead found releases are just printed
    out stdout.

    To run it, simply execute this file:

        $ python socorro/cron/jobs/ftpscraper.py

    If you want to override what date to run it for (by default it's
    "now") you simply use this format:

        $ python socorro/cron/jobs/ftpscraper.py --date=2015-10-23

    By default it runs for every, default configured, product
    (see the configuration set up in the FTPScraperCronApp above). You
    can override that like this:

        $ python socorro/cron/jobs/ftpscraper.py --product=mobile,thunderbird

    """

    required_config = Namespace()
    required_config.add_option(
        'date',
        default=datetime.datetime.utcnow(),
        doc='Date to run for',
        from_string_converter=string_to_datetime
    )
    required_config.add_option(
        'crontabber_job_class',
        default='socorro.cron.jobs.first_signatures.FirstSignaturesCronApp',
        doc="doesn't matter",
        from_string_converter=class_converter,
    )

    @staticmethod
    def get_application_defaults():
        return {
            'database.database_class': mock.MagicMock()
        }

    def __init__(self, config):
        self.config = config
        if isinstance(self.config.date, basestring):
            # Why isn't the from_string_converter converter called?!
            self.config.date = string_to_datetime(self.config.date)
        self.app = config.crontabber_job_class(config, {})

    def main(self):
        self.app.run(self.config.date)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(FirstSignaturesCronAppDryRunner))
