#! /usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This app submits crashes to a Socorro collector"""

import sys
import time

from configman import Namespace

from socorro.app.fetch_transform_save_app import FetchTransformSaveWithSeparateNewCrashSourceApp


class SubmitterApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    app_name = 'submitter_app'
    app_version = '3.1'
    app_description = __doc__
    config_module = 'socorro.submitter.config'

    required_config = Namespace()
    required_config.namespace('submitter')
    required_config.submitter.add_option(
        'delay',
        doc="pause between submission queuing in milliseconds",
        default='0',
        from_string_converter=lambda x: float(x) / 1000.0
    )
    required_config.submitter.add_option(
        'dry_run',
        doc="don't actually submit, just print product/version from raw crash",
        short_form='D',
        default=False
    )

    def _action_between_each_iteration(self):
        if self.config.submitter.delay:
            time.sleep(self.config.submitter.delay)

    def _action_after_iteration_completes(self):
        self.config.logger.info(
            'the queuing iterator is exhausted - waiting to quit'
        )
        self.task_manager.wait_for_empty_queue(
            5,
            "waiting for the queue to drain before quitting"
        )
        time.sleep(self.config.producer_consumer.number_of_threads * 2)

    def _filter_disallowed_values(self, current_value):
        """In this base class there are no disallowed values coming from the
        iterators.  Other users of these iterator may have some standards and
        can detect and reject them here

        """
        return current_value is None

    def _transform(self, crash_id):
        """Transfers raw data from the source to the destination without changing the data

        """
        if self.config.submitter.dry_run:
            print(crash_id)
        else:
            raw_crash = self.source.get_raw_crash(crash_id)
            dumps = self.source.get_raw_dumps_as_files(crash_id)
            self.destination.save_raw_crash_with_file_dumps(
                raw_crash,
                dumps,
                crash_id
            )


if __name__ == '__main__':
    sys.exit(SubmitterApp.run())
