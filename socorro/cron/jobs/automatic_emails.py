# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from configman import Namespace

from socorro.cron.base import PostgresBackfillCronApp
from socorro.external.exacttarget import exacttarget
from socorro.lib.datetimeutil import utc_now


def string_to_list(input_str):
    return [x.strip() for x in input_str.split(',') if x.strip()]


SQL_REPORTS = """
    SELECT DISTINCT r.email
    FROM reports r
        LEFT JOIN emails e ON r.email = e.email
    WHERE r.date_processed > %(start_date)s
    AND r.date_processed <= %(end_date)s
    AND r.email IS NOT NULL
    AND (e.last_sending < %(delayed_date)s OR e.last_sending IS NULL)
    AND r.product IN %(products)s
    ORDER BY r.email
"""


SQL_FIELDS = (
    'email',
)


SQL_UPDATE = """
    UPDATE emails
    SET last_sending = %(last_sending)s
    WHERE email = %(email)s
"""


SQL_INSERT = """
    INSERT INTO emails
    (email, last_sending)
    VALUES (%(email)s, %(last_sending)s)
"""


class AutomaticEmailsCronApp(PostgresBackfillCronApp):
    """Send an email to every user that crashes and gives us his or her email
    address. """

    app_name = 'automatic-emails'
    app_version = '1.0'
    app_description = 'Automatic Emails sent to users when they crash.'

    required_config = Namespace()
    required_config.add_option(
        'delay_between_emails',
        default=7,
        doc='Delay between two emails sent to the same user, in days. '
    )
    required_config.add_option(
        'restrict_products',
        default=['Firefox'],
        doc='List of products for which to send an email. ',
        from_string_converter=string_to_list
    )
    required_config.add_option(
        'exacttarget_user',
        default='',
        doc='ExactTarget API user. '
    )
    required_config.add_option(
        'exacttarget_password',
        default='',
        doc='ExactTarget API password. '
    )
    required_config.add_option(
        'email_template',
        default='',
        doc='Name of the email template to use in ExactTarget. '
    )
    required_config.add_option(
        'test_mode',
        default=False,
        doc='Activate the test mode, in which all email addresses are '
            'replaced by the one in test_email_address. Use it to avoid '
            'sending unexpected emails to your users. '
    )
    required_config.add_option(
        'test_email_address',
        default='test@example.org',
        doc='In test mode, send all emails to this email address. '
    )

    def __init__(self, *args, **kwargs):
        super(AutomaticEmailsCronApp, self).__init__(*args, **kwargs)
        self.email_service = exacttarget.ExactTarget(
            user=self.config.exacttarget_user,
            pass_=self.config.exacttarget_password
        )

    def run(self, connection, run_datetime):
        logger = self.config.logger
        cursor = connection.cursor()

        if self.config.test_mode:
            logger.warning('You are running Automatic Emails cron app '
                           'in test mode')

        delay = datetime.timedelta(days=self.config.delay_between_emails)
        sql_params = {
            'start_date': run_datetime - datetime.timedelta(hours=1),
            'end_date': run_datetime,
            'delayed_date': run_datetime - delay,
            'products': tuple(self.config.restrict_products)
        }

        cursor.execute(SQL_REPORTS, sql_params)
        for row in cursor.fetchall():
            report = dict(zip(SQL_FIELDS, row))
            self.send_email(report)
            self.update_user(report, utc_now(), connection)
            #logger.info('Automatic Email sent to %s', report['email'])

    def send_email(self, report):
        logger = self.config.logger
        list_service = self.email_service.list()
        email = report['email'].strip()

        if self.config.test_mode:
            email = self.config.test_email_address

        if not email:
            # Don't send anything to empty email addresses
            return

        try:
            subscriber = list_service.get_subscriber(
                email,
                None,
                ['token']
            )
            subscriber_key = subscriber['token'] or email
        except exacttarget.NewsletterException:
            # subscriber does not exist, let's give it an ID
            subscriber_key = email

        fields = {
            'EMAIL_ADDRESS_': email,
            'EMAIL_FORMAT_': 'H',
            'TOKEN': subscriber_key
        }
        try:
            self.email_service.trigger_send(self.config.email_template, fields)
        except exacttarget.NewsletterException, error_msg:
            logger.error(
                'Unable to send an email to %s, error is: %s',
                email, str(error_msg), exc_info=True
            )


    def update_user(self, report, sending_datetime, connection):
        cursor = connection.cursor()
        sql_params = {
            'email': report['email'],
            'last_sending': sending_datetime
        }
        cursor.execute(SQL_UPDATE, sql_params)
        if cursor.rowcount == 0:
            # This email address is not known yet, insert it
            cursor.execute(SQL_INSERT, sql_params)
        connection.commit()
