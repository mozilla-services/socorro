import datetime
import csv
import sys
from cStringIO import StringIO

from configman import Namespace
from configman.converters import class_converter
from crontabber.base import BaseCronApp
from crontabber.mixins import with_postgres_transactions

from socorro.external.postgresql.missing_symbols import MissingSymbols
from socorro.app.socorro_app import App


@with_postgres_transactions()
class MissingSymbolsCronApp(BaseCronApp):
    app_name = 'missing-symbols'
    app_description = 'Missing Symbols'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'hours_back',
        default=24,  # hours
        doc='Number of hours of missing symbols'
    )

    required_config.add_option(
        'boto_class',
        default=(
            'socorro.external.boto.connection_context.S3ConnectionContext'
        ),
        doc=(
            'fully qualified dotted Python classname to handle '
            'Boto connections',
        ),
        from_string_converter=class_converter,
        reference_value_from='resource.boto'
    )

    required_config.add_option(
        'bucket_name',
        default='missing-symbols',
        doc='Name of S3 bucket to store this'
    )

    def run(self):
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow((
            'debug_file',
            'debug_id',
            'code_file',
            'code_id',
        ))
        implementation = MissingSymbols(config=self.config)
        date = datetime.datetime.utcnow()
        date -= datetime.timedelta(hours=self.config.hours_back)
        rows = 0
        for each in implementation.iter(date=date.date()):
            writer.writerow((
                each['debug_file'],
                each['debug_id'],
                each['code_file'],
                each['code_id'],
            ))
            rows += 1
        s3 = self.config.boto_class(self.config)
        conn = s3._connect()
        self.config.logger.info(
            'Writing {} missing symbols rows to a file in {}'.format(
                format(rows, ','),
                self.config.bucket_name
            )
        )
        bucket = s3._get_or_create_bucket(conn, self.config.bucket_name)
        key_object = bucket.new_key('latest.csv')
        key_object.set_contents_from_string(buf.getvalue())
        self.config.logger.info(
            'Generated {} ({} bytes, {:.2f} Mb)'.format(
                key_object.generate_url(expires_in=0, query_auth=False),
                format(key_object.size, ','),
                key_object.size / 1024.0 / 1024.0
            )
        )


class MissingSymbolsCronAppDryRunner(App):  # pragma: no cover
    """App to test running missing-symbols right here right now.

    To run it, simply execute this file:

        $ python socorro/cron/jobs/missingsymbols.py

    """

    required_config = Namespace()
    required_config.add_option(
        'crontabber_job_class',
        default='socorro.cron.jobs.missingsymbols.MissingSymbolsCronApp',
        doc='bla',
        from_string_converter=class_converter,
    )

    def __init__(self, config):
        self.config = config
        self.app = config.crontabber_job_class(config, {})

    def main(self):
        self.app.run()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(MissingSymbolsCronAppDryRunner.run())
