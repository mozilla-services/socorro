# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from email.utils import parseaddr

from configman import Namespace

from socorro.cron.base import PostgresBackfillCronApp
from socorro.external.exacttarget import exacttarget
from socorro.lib.datetimeutil import utc_now


def string_to_list(input_str):
    return [x.strip() for x in input_str.split(',') if x.strip()]


class EditDistance(object):
    """
    Match one string against a list of known strings using edit distance 1.
    """
    def __init__(self, against, alphabet=u'abcdefghijklmnopqrstuvwxyz'):
        self.against = against
        self.alphabet = alphabet

    def match(self, word):
        return list(self._match(word))

    def _match(self, word):
        for w in self._edits1(word):
            if w in self.against:
                yield w

    def _edits1(self, word):
        n = len(word)
        return set(
            # deletion
            [word[0:i] + word[i + 1:] for i in range(n)] +
            # transposition
            [word[0:i] + word[i + 1] + word[i] + word[i + 2:]
             for i in range(n - 1)] +
            # alteration
            [word[0:i] + c + word[i + 1:]
             for i in range(n) for c in self.alphabet] +
            # insertion
            [word[0:i] + c + word[i:] for i in range(n + 1)
             for c in self.alphabet]
        )


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
        doc='Delay between two emails sent to the same user, in days. ',
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
        doc='ExactTarget API user. ',
        reference_value_from='secrets.exacttarget',
    )
    required_config.add_option(
        'exacttarget_password',
        default='',
        doc='ExactTarget API password. ',
        reference_value_from='secrets.exacttarget',
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
    # the following list of email domains is taken from looking through many
    # days of errors from crontabbers.log and noticing repeatedly common
    # domains that have failed that could easily be corrected
    required_config.add_option(
        'common_email_domains',
        default=[
            'gmail.com', 'yahoo.com', 'hotmail.com', 'comcast.net',
            'mail.ru', 'aol.com', 'outlook.com', 'facebook.com',
            'mail.com',
        ],
        doc='List of known/established email domains to use when trying to '
            'correct possible simple typos',
        from_string_converter=string_to_list
    )

    def __init__(self, *args, **kwargs):
        super(AutomaticEmailsCronApp, self).__init__(*args, **kwargs)
        self.email_service = exacttarget.ExactTarget(
            user=self.config.exacttarget_user,
            pass_=self.config.exacttarget_password
        )

    @property
    def edit_distance(self):
        # make it a property so it can be reused if need be
        if not getattr(self, '_edit_distance', None):
            self._edit_distance = EditDistance(
                self.config.common_email_domains,
                alphabet='abcdefghijklmnopqrstuvwxyz.'
            )
        return self._edit_distance

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

        if self.config.test_mode:
            email = self.config.test_email_address
        else:
            try:
                email = report['email'].decode('utf-8')
            except UnicodeDecodeError:
                # we are not able to send emails to addresses containing
                # non-UTF-8 characters, thus filtering them out
                return
            # In case the email field contains a string like
            # `Bob <bob@example.com>` then we only want the
            # `bob@example.com` part.
            email = parseaddr(email)[1]

        if not (email.count('@') == 1 and email.split('@')[1].count('.') >= 1):
            # this does not look like an email address, we don't try to send
            # anything to it
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
        except Exception, error_msg:
            # suds raises bare Python Exceptions, so we test if it's one that
            # we expect and raise it if not
            if 'Bad Request' in str(error_msg):
                subscriber_key = email
            else:
                raise

        # clean up the easy mistakes
        new_email = self.correct_email(email)
        if new_email:
            # for example, it might correct `foo@mail.com.` to `foo@mail.com`
            email = new_email

        fields = {
            'EMAIL_ADDRESS_': email,
            'EMAIL_FORMAT_': 'H',
            'TOKEN': subscriber_key
        }
        try:
            self.email_service.trigger_send(self.config.email_template, fields)
        except exacttarget.NewsletterException, error_msg:
            # could it be because the email address is peterbe@gmai.com
            # instead of peterbe@gmail.com??
            better_email = self.correct_email(email, typo_correct=True)
            if better_email:
                try:
                    fields['EMAIL_ADDRESS_'] = better_email
                    self.email_service.trigger_send(
                        self.config.email_template, fields
                    )
                except exacttarget.NewsletterException, error_msg:
                    # even that didn't help, could be that we corrected
                    # banned@htmail.com to banned@hotmail.com but still banned
                    logger.error(
                        'Unable to send a corrected email to %s, '
                        'error is: %s',
                        better_email, str(error_msg), exc_info=True
                    )
            else:
                # then we're stumped and not much we can do
                logger.error(
                    'Unable to send an email to %s, error is: %s',
                    email, str(error_msg), exc_info=True
                )
        except Exception, error_msg:
            # suds raises bare Python Exceptions, so we test if it's one that
            # we expect and raise it if not
            if 'Bad Request' in str(error_msg):
                logger.error(
                    'Unable to send an email to %s, fields are %s, '
                    'error is: %s',
                    email, str(fields), str(error_msg), exc_info=True
                )
            else:
                raise

    def correct_email(self, email, typo_correct=False):
        """return a corrected email if we can or else return None"""
        if email.count('@') != 1:
            return
        pre, domain = email.split('@')
        original_domain = domain
        domain = domain.lower()
        if domain.startswith('.'):
            domain = domain[1:]
        if domain.endswith('.'):
            domain = domain[:-1]
        if domain:
            if typo_correct:
                matched = self.edit_distance.match(domain)
                if len(matched) == 1:
                    return '%s@%s' % (pre, matched[0])
            elif original_domain != domain:
                # it changed!
                return '%s@%s' % (pre, domain)

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
