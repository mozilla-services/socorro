# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from configman import Namespace
from socorro.cron.base import BaseBackfillCronApp, SubprocessMixin


class CommandError(Exception):
    pass


class ModulelistCronApp(BaseBackfillCronApp, SubprocessMixin):
    app_name = 'modulelist'
    app_description = 'Runs the modulelist pig job'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'pig_classpath',
        default='/data/socorro/analysis/',
        doc='Sets the PIG_CLASSPATH for running the pig job',
    )
    required_config.add_option(
        'output_file',
        default='/mnt/crashanalysis/crash_analysis/modulelist/'
                '%(output_date)s-modulelist.txt',
        doc='File passed to `hadoop fs -getmerge ...`. The `date` parameter '
            'becomes the formatted (%Y%m%d) date of the input date'
    )

    def run(self, date):
        logger = self.config.logger
        yesterday = date - datetime.timedelta(days=1)

        data = {
            'pig_classpath': self.config.pig_classpath,
            'date': yesterday.strftime('%Y%m%d'),
        }
        # This one is a bit odd since it depends on the `output_date`
        # variable.
        data['output_file'] = self.config.output_file % data

        pig_command = (
            'PIG_CLASSPATH=%(pig_classpath)s '
            'pig -param start_date=%(date)s -param end_date=%(date)s '
            '%(pig_classpath)s/modulelist.pig'
            % data
        )

        hadoop_command_1 = (
            'PIG_CLASSPATH=%(pig_classpath)s '
            'hadoop fs -getmerge modulelist-%(date)s-%(date)s %(output_file)s'
            % data
        )

        hadoop_command_2 = (
            'PIG_CLASSPATH=%(pig_classpath)s '
            'hadoop fs -rmr modulelist-%(date)s-%(date)s'
            % data
        )

        exit_code, stdout, stderr = self.run_process(pig_command)
        if exit_code:
            stdout and logger.error(stdout)
            stderr and logger.error(stderr)
            raise CommandError(
                'pig run failed (%s)' % (pig_command,)
            )
        else:
            if stdout:
                logger.info(stdout)
            if stderr:
                logger.info(stderr)

        exit_code, stdout, stderr = self.run_process(hadoop_command_1)
        if exit_code:
            stdout and logger.error(stdout)
            stderr and logger.error(stderr)
            raise CommandError(
                'hadoop getmerge failed (%s)' % (hadoop_command_1,)
            )
        else:
            if stdout:
                logger.info(stdout)
            if stderr:
                logger.info(stderr)

        exit_code, stdout, stderr = self.run_process(hadoop_command_2)
        if exit_code:
            stdout and logger.error(stdout)
            stderr and logger.error(stderr)
            raise CommandError(
                'hadoop cleanup failed (%s)' % (hadoop_command_2,)
            )
        else:
            if stdout:
                logger.info(stdout)
            if stderr:
                logger.info(stderr)
