#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""this app will move crashes from one storage location to another"""

from configman import Namespace

from socorro.app.fetch_transform_save_app import (
    FetchTransformSaveApp,
    FetchTransformSaveWithSeparateNewCrashSourceApp,
    main
)
from socorro.external.crashstorage_base import (
    CrashIDNotFound,
)


#==============================================================================
class CrashMoverApp(FetchTransformSaveApp):
    app_name = 'crashmover'
    app_version = '2.0'
    app_description = __doc__

    required_config = Namespace()


#==============================================================================
class RawAndProcessedCopierApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    """copy raw & processed crashes from a source to a destination"""
    app_name = 'raw_and_processed_crash_copier'
    app_version = '1.0'
    app_description = __doc__

    #--------------------------------------------------------------------------
    @staticmethod
    def get_application_defaults():
        return {
            'source.crashstorage_class':
                'socorro.external.boto.crashstorage.BotoS3CrashStorage',
            "destination.crashstorage_class":
                'socorro.external.es.crashstorage.'
                'ESCrashStorageNoStackwalkerOutput',
        }

    #--------------------------------------------------------------------------
    def _transform(self, crash_id):
        """this implementation is the framework on how a raw crash is
        converted into a processed crash.  The 'crash_id' passed in is used as
        a key to fetch the raw crash from the 'source', the conversion funtion
        implemented by the 'processor_class' is applied, the
        processed crash is saved to the 'destination', and then 'finished_func'
        is called."""
        try:
            raw_crash = self.source.get_raw_crash(crash_id)
            processed_crash = self.source.get_processed(
                crash_id
            )
        except CrashIDNotFound:
            self.processor.reject_raw_crash(
                crash_id,
                'this crash cannot be found in raw crash storage'
            )
            return
        except Exception, x:
            self.config.logger.warning(
                'error loading crash %s',
                crash_id,
                exc_info=True
            )
            self.processor.reject_raw_crash(
                crash_id,
                'error in loading: %s' % x
            )
            return

        if 'uuid' not in raw_crash:
            raw_crash.uuid = crash_id
        self.destination.save_raw_and_processed(
            raw_crash,
            None,
            processed_crash,
            crash_id
        )
        self.config.logger.info('saved - %s', crash_id)

if __name__ == '__main__':
    main(CrashMoverApp)
