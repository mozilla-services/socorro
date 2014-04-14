# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace
from socorro.cron.crontabber import BaseCronApp


class BuggyCronApp(BaseCronApp):
    app_name = 'buggy'
    app_description = 'Does some bar things'

    required_config = Namespace()
    required_config.add_option(
        'bugzilla_url',
        default='https://bugs.mozilla.org',
        doc='Base URL where the bugz live'
    )

    def run(self):
        print "DOING something with", self.config.bugzilla_url
