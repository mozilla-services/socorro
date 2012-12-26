#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This app tests that automatic emails are being sent via ExactTarget. It
sends one sample email to the passed email address. You need to check your
email inbox after running this app to verify that you received the email. """

# This app can be invoked like this:
#     .../socorro/integrationtest/test_automatic_emails_app.py --help
# set your path to make that simpler
# set both socorro and configman in your PYTHONPATH

from configman import Namespace

from socorro.app import generic_app
from socorro.cron.jobs.automatic_emails import AutomaticEmailsCronApp


class IntegrationTestAutomaticEmailsApp(generic_app.App):
    app_name = 'test_automatic_emails'
    app_version = '0.1'
    app_description = __doc__

    required_config = Namespace()
    required_config.add_option(
        'automatic_emails_class',
        default=AutomaticEmailsCronApp,
        doc='The class to use to send automatic emails.'
    )
    required_config.add_option(
        'tester_email_address',
        default='',
        doc='Send the automatic email to this address.'
    )

    def main(self):
        emailer = self.config.automatic_emails_class(self.config, '')

        report = {
            'email': self.config.tester_email_address,
        }

        print emailer.send_email(report)

if __name__ == '__main__':
    generic_app.main(IntegrationTestAutomaticEmailsApp)
