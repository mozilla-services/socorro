#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""this app will move crashes from one storage location to another"""

from configman import Namespace

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp, main


#==============================================================================
class CrashMoverApp(FetchTransformSaveApp):
    app_name = 'crashmover'
    app_version = '2.0'
    app_description = __doc__

    required_config = Namespace()


if __name__ == '__main__':
    main(CrashMoverApp)
