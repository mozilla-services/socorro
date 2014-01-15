# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import elasticutils
from email.utils import parseaddr
from pyelasticsearch.exceptions import ElasticHttpNotFoundError

from configman import Namespace
from configman.converters import class_converter, list_converter

from socorro.cron.base import BaseBackfillCronApp
from socorro.lib.transform_rules import TransformRuleSystem
from socorro.external.elasticsearch.base import ElasticSearchBase
from socorro.external.elasticsearch.supersearch import SuperS
from socorro.external.exacttarget import exacttarget


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


def sanitize_email(data_dict):
    data_dict['processed_crash.email'] = \
        data_dict['processed_crash.email'].strip()
    return True


def set_email_template(data_dict, template):
    data_dict['email_template'] = template
    return True


def verify_email(data_dict):
    return bool(data_dict['processed_crash.email'])


def verify_email_last_sending(data_dict, emails_list={}):
    return not bool(emails_list.get(data_dict['processed_crash.email'], False))


def verify_support_classification(data_dict, classification):
    key = 'processed_crash.classifications.support.classification'
    if key not in data_dict:
        return False
    return data_dict[key] == classification


class AutomaticEmailsCronApp(BaseBackfillCronApp, ElasticSearchBase):
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
        from_string_converter=list_converter
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
        from_string_converter=list_converter
    )

    required_config.namespace('elasticsearch')
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.elasticsearch.connection_context.'
                'ConnectionContext',
        from_string_converter=class_converter
    )
    required_config.elasticsearch.add_option(
        'index_creator_class',
        default='socorro.external.elasticsearch.crashstorage.'
                'ElasticSearchCrashStorage',
        from_string_converter=class_converter
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

    def run(self, run_datetime):
        logger = self.config.logger

        if self.config.test_mode:
            logger.warning('You are running Automatic Emails cron app '
                           'in test mode')

        delay = datetime.timedelta(days=self.config.delay_between_emails)
        params = {
            'start_date': run_datetime - datetime.timedelta(hours=1),
            'end_date': run_datetime,
            'delayed_date': run_datetime - delay,
            'products': tuple(self.config.restrict_products)
        }

        # Find the indexes to use to optimize the elasticsearch query.
        indexes = self.generate_list_of_indexes(
            params['start_date'],
            params['end_date'],
            self.config.elasticsearch.elasticsearch_index
        )

        # Create and configure the search object.
        connection = SuperS().es(
            urls=self.config.elasticsearch.elasticsearch_urls,
            timeout=self.config.elasticsearch.elasticsearch_timeout,
        )
        search = (connection.indexes(*indexes)
                            .doctypes(
                                self.config.elasticsearch.elasticsearch_doctype
                            )
                            .order_by('processed_crash.email'))

        # Create filters.
        args_and = {
            'processed_crash.date_processed__lt': params['end_date'],
            'processed_crash.date_processed__gt': params['start_date'],
            'processed_crash.product': [x.lower() for x in params['products']],
        }
        args_not = {
            'processed_crash.email__missing': None,
        }

        filters = elasticutils.F(**args_and)
        filters &= ~elasticutils.F(**args_not)

        search = search.filter(filters)
        count = search.count()  # Total number of results.
        search = search[:count]

        # Get the recently sent emails
        emails = self.get_list_of_emails(params, connection)

        validation_rules = TransformRuleSystem()
        validation_rules.load_rules((
            (verify_email, (), {}, sanitize_email, (), {}),
            (verify_email, (), {}, False, (), {}),
            (
                verify_email_last_sending, (), {'emails_list': emails},
                True, (), {}
            ),
        ))

        template_rules = TransformRuleSystem()
        template_rules.load_rules((
            (
                verify_support_classification, ('bitguard',), {},
                set_email_template, ('socorro_bitguard_en',), {}
            ),
            # If no other rule passed, fall back to the default template.
            (
                True, (), {},
                set_email_template, (self.config.email_template,), {}
            ),
        ))

        for hit in search.values_dict(
            'processed_crash.email',
            'processed_crash.classifications.support.classification',
        ):
            res = validation_rules.apply_until_predicate_fails(hit)

            if res is None:  # All predicates succeeded!
                # Now apply all template rules to find which email template
                # to use.
                template_rules.apply_until_action_succeeds(hit)

                email = hit['processed_crash.email']
                self.send_email(hit)
                self.update_user(email, run_datetime, connection.get_es())
                emails[email] = run_datetime
                # logger.info('Automatic Email sent to %s', email)

        # Make sure the next run will have updated data, to avoid sending an
        # email several times.
        connection.get_es().refresh()

    def send_email(self, report):
        email = report['processed_crash.email']
        email_template = report['email_template']

        logger = self.config.logger
        list_service = self.email_service.list()

        if self.config.test_mode:
            email = self.config.test_email_address
        else:
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
            self.email_service.trigger_send(email_template, fields)
        except exacttarget.NewsletterException, error_msg:
            # could it be because the email address is peterbe@gmai.com
            # instead of peterbe@gmail.com??
            better_email = self.correct_email(email, typo_correct=True)
            if better_email:
                try:
                    fields['EMAIL_ADDRESS_'] = better_email
                    self.email_service.trigger_send(
                        email_template, fields
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

    def update_user(self, email, sending_datetime, connection):
        document = {
            'last_sending': sending_datetime
        }
        connection.index(
            index=self.config.elasticsearch.elasticsearch_emails_index,
            doc_type='emails',
            doc=document,
            id=email,
            overwrite_existing=True,
        )

    def get_list_of_emails(self, params, connection):
        emails_index = self.config.elasticsearch.elasticsearch_emails_index

        search = connection.indexes(emails_index)
        search = search.doctypes('emails')
        search = search.filter(last_sending__gt=params['delayed_date'])

        emails = {}
        try:
            res = search.execute()
            for hit in res.results:
                emails[hit['_id']] = hit['_source']['last_sending']
        except ElasticHttpNotFoundError:
            # If the emails index does not exist, that means it's the first
            # time this script runs, and we should create the index.
            index_creator = self.config.elasticsearch.index_creator_class(
                self.config.elasticsearch
            )
            index_creator.create_emails_index()

        return emails
