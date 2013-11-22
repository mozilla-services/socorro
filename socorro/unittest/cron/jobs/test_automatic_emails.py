# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import mock
from nose.plugins.attrib import attr

from configman import ConfigurationManager

from socorro.cron import crontabber
from socorro.cron.jobs import automatic_emails
from socorro.external.exacttarget import exacttarget
from socorro.external.elasticsearch.crashstorage import \
    ElasticSearchCrashStorage
from socorro.external.elasticsearch.supersearch import SuperS
from socorro.lib.datetimeutil import string_to_datetime, utc_now
from ..base import IntegrationTestCaseBase, TestCaseBase

# Remove debugging noise during development
# import logging
# logging.getLogger('pyelasticsearch').setLevel(logging.ERROR)
# logging.getLogger('elasticutils').setLevel(logging.ERROR)


#==============================================================================
class TestAutomaticEmails(TestCaseBase):

    def _setup_simple_config(self, domains=None):
        conf = automatic_emails.AutomaticEmailsCronApp.get_required_config()
        conf.add_option('logger', default=mock.Mock())

        return ConfigurationManager(
            [conf],
            values_source_list=[{
                'common_email_domains': domains,
            }],
            argv_source=[]
        )

    def test_correct_email(self):
        domains = ('gmail.com', 'yahoo.com')
        config_manager = self._setup_simple_config(domains=domains)
        with config_manager.context() as config:
            app = automatic_emails.AutomaticEmailsCronApp(config, '')
            # easy corrections
            self.assertEqual(
                app.correct_email('peterbe@YAHOOO.COM', typo_correct=True),
                'peterbe@yahoo.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@gmai.com', typo_correct=True),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@gmaill.com', typo_correct=True),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                # case insensitive
                app.correct_email('peterbe@Gamil.com', typo_correct=True),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@gmaiK.com', typo_correct=True),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@gmail..com', typo_correct=True),
                'peterbe@gmail.com'
            )

            # dots here and there
            self.assertEqual(
                app.correct_email('peterbe@gmail.com.'),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@.gmail.com'),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@.gmail.com.'),
                'peterbe@gmail.com'
            )

            # dots and typos
            self.assertEqual(
                # case insensitive
                app.correct_email('peterbe@Gamil.com.', typo_correct=True),
                'peterbe@gmail.com'
            )

            # What doesn't work are edit distances greater than 1
            self.assertFalse(app.correct_email('peterbe@gamill.com'))
            self.assertFalse(app.correct_email('peterbe@gmil.cam'))
            # and don't mess with @ signs
            self.assertFalse(
                app.correct_email('peterbe@hotmail.com@gamil.com')
            )

    def test_correct_ambiguous_email(self):
        domains = ('gmail.com', 'yahoo.com', 'mail.com')
        config_manager = self._setup_simple_config(domains=domains)
        with config_manager.context() as config:
            app = automatic_emails.AutomaticEmailsCronApp(config, '')
            # because 'gmail.com' and 'mail.com' is so similar,
            # we don't want correction of 'mail.com' to incorrectly
            # become 'gmail.com'
            self.assertEqual(
                app.correct_email('peterbe@gmail.com', typo_correct=True),
                None
            )
            self.assertEqual(
                app.correct_email('peterbe@mail.com', typo_correct=True),
                None
            )


#==============================================================================
@attr(integration='elasticsearch')
class IntegrationTestAutomaticEmails(IntegrationTestCaseBase):

    def setUp(self):
        super(IntegrationTestAutomaticEmails, self).setUp()
        # prep a fake table
        now = utc_now() - datetime.timedelta(minutes=30)
        last_month = now - datetime.timedelta(days=31)

        config_manager = self._setup_storage_config()
        with config_manager.context() as config:
            storage = ElasticSearchCrashStorage(config)
            # clear the indices cache so the index is created on every test
            storage.indices_cache = set()

            storage.save_processed({
                'uuid': '1',
                'email': 'someone@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now,
                'classifications': {
                    'support': {
                        'classification': 'unknown'
                    }
                }
            })
            storage.save_processed({
                'uuid': '2',
                'email': '"Quidam" <quidam@example.com>',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now,
                'classifications': {
                    'support': {
                        'classification': None
                    }
                }
            })
            storage.save_processed({
                'uuid': '3',
                'email': 'anotherone@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now,
                'classifications': {
                    'support': {
                        'classification': 'bitguard'
                    }
                }
            })
            storage.save_processed({
                'uuid': '4',
                'email': 'a@example.org',
                'product': 'NightlyTrain',
                'version': '1.0',
                'release_channel': 'Nightly',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '5',
                'email': 'b@example.org',
                'product': 'NightlyTrain',
                'version': '1.0',
                'release_channel': 'Nightly',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '6',
                'email': 'c@example.org',
                'product': 'NightlyTrain',
                'version': '1.0',
                'release_channel': 'Nightly',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '7',
                'email': 'd@example.org',
                'product': 'NightlyTrain',
                'version': '1.0',
                'release_channel': 'Nightly',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '8',
                'email': 'e@example.org',
                'product': 'NightlyTrain',
                'version': '1.0',
                'release_channel': 'Nightly',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '9',
                'email': 'me@my.name',
                'product': 'EarthRaccoon',
                'version': '1.0',
                'release_channel': 'Nightly',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '18',
                'email': 'z\xc3\x80drian@example.org',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now
            })

            # Let's insert a duplicate
            storage.save_processed({
                'uuid': '10',
                'email': 'anotherone@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now
            })

            # And let's insert some invalid crashes
            storage.save_processed({
                'uuid': '11',
                'email': None,
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '12',
                'email': 'myemail@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': last_month
            })
            storage.save_processed({
                'uuid': '13',
                'email': 'menime@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '14',
                'email': 'hi@mynameis.slim',
                'product': 'WindBear',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now
            })

            # Finally some invalid email addresses
            storage.save_processed({
                'uuid': '15',
                'email': '     ',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '16',
                'email': 'invalid@email',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now
            })
            storage.save_processed({
                'uuid': '17',
                'email': 'i.do.not.work',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': now
            })

            # Create some email addresses.
            storage.create_emails_index()
            storage.es.index(
                index=config.elasticsearch_emails_index,
                doc_type='emails',
                doc={
                    'email': 'someone@example.com',
                    'last_sending': last_month
                },
                id='someone@example.com',
            )
            storage.es.index(
                index=config.elasticsearch_emails_index,
                doc_type='emails',
                doc={
                    'email': '"Quidam" <quidam@example.com>',
                    'last_sending': last_month
                },
                id='"Quidam" <quidam@example.com>',
            )
            storage.es.index(
                index=config.elasticsearch_emails_index,
                doc_type='emails',
                doc={
                    'email': 'menime@example.com',
                    'last_sending': now
                },
                id='menime@example.com',
            )

            # As indexing is asynchronous, we need to force elasticsearch to
            # make the newly created content searchable before we run the
            # tests.
            storage.es.refresh()

    def tearDown(self):
        config_manager = self._setup_storage_config()
        with config_manager.context() as config:
            storage = ElasticSearchCrashStorage(config)
            storage.es.delete_index(config.elasticsearch_index)
            storage.es.delete_index(config.elasticsearch_emails_index)
            storage.es.flush()

        super(IntegrationTestAutomaticEmails, self).tearDown()

    def _setup_config_manager(
        self,
        delay_between_emails=7,
        exacttarget_user='',
        exacttarget_password='',
        restrict_products=['WaterWolf'],
        email_template='socorro_dev_test'
    ):
        extra_value_source = {
            'crontabber.class-AutomaticEmailsCronApp.delay_between_emails':
                delay_between_emails,
            'crontabber.class-AutomaticEmailsCronApp.exacttarget_user':
                exacttarget_user,
            'crontabber.class-AutomaticEmailsCronApp.exacttarget_password':
                exacttarget_password,
            'crontabber.class-AutomaticEmailsCronApp.restrict_products':
                restrict_products,
            'crontabber.class-AutomaticEmailsCronApp.email_template':
                email_template,
            'crontabber.class-AutomaticEmailsCronApp.elasticsearch.'
            'elasticsearch_index':
                'socorro_integration_test',
            'crontabber.class-AutomaticEmailsCronApp.elasticsearch.'
            'elasticsearch_emails_index':
                'socorro_integration_test_emails',
        }

        return super(
            IntegrationTestAutomaticEmails,
            self
        )._setup_config_manager(
            'socorro.cron.jobs.automatic_emails.AutomaticEmailsCronApp|1h',
            extra_value_source=extra_value_source
        )

    def _setup_simple_config(self, common_email_domains=None):
        conf = automatic_emails.AutomaticEmailsCronApp.get_required_config()
        conf.add_option('logger', default=mock.Mock())

        values_source_list = {
            'delay_between_emails': 7,
            'exacttarget_user': '',
            'exacttarget_password': '',
            'restrict_products': ['WaterWolf'],
            'email_template': 'socorro_dev_test',
            'elasticsearch.elasticsearch_index': 'socorro_integration_test',
            'elasticsearch.elasticsearch_emails_index':
                'socorro_integration_test_emails',
        }
        if common_email_domains:
            values_source_list['common_email_domains'] = common_email_domains
        return ConfigurationManager(
            [conf],
            values_source_list=[values_source_list],
            argv_source=[]
        )

    def _setup_test_mode_config(self):
        conf = automatic_emails.AutomaticEmailsCronApp.get_required_config()
        conf.add_option('logger', default=mock.Mock())

        return ConfigurationManager(
            [conf],
            values_source_list=[{
                'delay_between_emails': 7,
                'exacttarget_user': '',
                'exacttarget_password': '',
                'restrict_products': ['WaterWolf'],
                'test_mode': True,
                'email_template': 'socorro_dev_test',
                'elasticsearch.elasticsearch_index':
                    'socorro_integration_test',
                'elasticsearch.elasticsearch_emails_index':
                    'socorro_integration_test_emails',
            }],
            argv_source=[]
        )

    def _setup_storage_config(self):
        storage_conf = ElasticSearchCrashStorage.get_required_config()
        storage_conf.add_option('logger', default=mock.Mock())

        return ConfigurationManager(
            [storage_conf],
            values_source_list=[{
                'elasticsearch_index': 'socorro_integration_test',
                'elasticsearch_emails_index': 'socorro_integration_test_emails'
            }],
            argv_source=[]
        )

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_cron_job(self, exacttarget_mock):
        config_manager = self._setup_config_manager()
        et_mock = exacttarget_mock.return_value

        # Make get_subscriber raise an exception
        list_service = et_mock.list.return_value = mock.Mock()
        list_service.get_subscriber = mock.Mock(
            side_effect=exacttarget.NewsletterException()
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['automatic-emails']
            assert not information['automatic-emails']['last_error']
            assert information['automatic-emails']['last_success']
            self.assertEqual(et_mock.trigger_send.call_count, 4)

            last_email = u'z\xc0drian@example.org'

            # Verify the last call to trigger_send
            fields = {
                'EMAIL_ADDRESS_': last_email,
                'EMAIL_FORMAT_': 'H',
                'TOKEN': last_email
            }

            et_mock.trigger_send.assert_called_with('socorro_dev_test', fields)

            # Verify that user's data was updated
            conf = config.crontabber['class-AutomaticEmailsCronApp']
            es = SuperS().es(
                urls=conf.elasticsearch.elasticsearch_urls,
                timeout=conf.elasticsearch.elasticsearch_timeout,
            )
            search = es.indexes(conf.elasticsearch.elasticsearch_emails_index)
            search = search.doctypes('emails')
            es.get_es().refresh()

            emails_list = (
                'someone@example.com',
                '"Quidam" <quidam@example.com>',
                'anotherone@example.com'
            )
            search = search.filter(_id__in=emails_list)
            res = search.values_list('last_sending')
            self.assertEqual(len(res), 3)
            now = utc_now()
            for row in res:
                date = string_to_datetime(row[0])
                self.assertEqual(date.year, now.year)
                self.assertEqual(date.month, now.month)
                self.assertEqual(date.day, now.day)

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_run(self, exacttarget_mock):
        # Verify that classifications work.
        def mocked_trigger_send(email_template, fields):
            if fields['EMAIL_ADDRESS_'] == 'anotherone@example.com':
                self.assertEqual(email_template, 'socorro_bitguard_en')
            else:
                self.assertEqual(email_template, 'socorro_dev_test')

        exacttarget_mock.return_value.trigger_send.side_effect = \
            mocked_trigger_send

        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')
            job.run(utc_now())

            et_mock = exacttarget_mock.return_value
            self.assertEqual(et_mock.trigger_send.call_count, 4)

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_run_with_classifications(self, exacttarget_mock):
        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')
            job.run(utc_now())

            et_mock = exacttarget_mock.return_value
            self.assertEqual(et_mock.trigger_send.call_count, 4)

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_send_email(self, exacttarget_mock):
        list_service_mock = exacttarget_mock.return_value.list.return_value
        list_service_mock.get_subscriber.return_value = {
            'token': 'fake@example.com'
        }

        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            email = 'fake@example.com'
            job.send_email({
                'processed_crash.email': email,
                'email_template': 'socorro_dev_test',
            })

            fields = {
                'EMAIL_ADDRESS_': email,
                'EMAIL_FORMAT_': 'H',
                'TOKEN': email
            }
            exacttarget_mock.return_value.trigger_send.assert_called_with(
                'socorro_dev_test',
                fields
            )

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_send_email_test_mode(self, exacttarget_mock):
        list_service_mock = exacttarget_mock.return_value.list.return_value
        list_service_mock.get_subscriber.return_value = {
            'token': 'fake@example.com'
        }

        config_manager = self._setup_test_mode_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            email = 'fake@example.com'
            job.send_email({
                'processed_crash.email': email,
                'email_template': 'socorro_dev_test',
            })

            fields = {
                'EMAIL_ADDRESS_': config.test_email_address,
                'EMAIL_FORMAT_': 'H',
                'TOKEN': 'fake@example.com'
            }
            exacttarget_mock.return_value.trigger_send.assert_called_with(
                'socorro_dev_test',
                fields
            )

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_error_in_send_email(self, exacttarget_mock):
        list_service_mock = exacttarget_mock.return_value.list.return_value
        list_service_mock.get_subscriber.return_value = {
            'token': 'fake@example.com'
        }

        exacttarget_mock.return_value.trigger_send.side_effect = (
            exacttarget.NewsletterException('error')
        )

        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            email = 'fake@example.com'
            job.send_email({
                'processed_crash.email': email,
                'email_template': 'socorro_dev_test',
            })

            fields = {
                'EMAIL_ADDRESS_': email,
                'EMAIL_FORMAT_': 'H',
                'TOKEN': email
            }
            exacttarget_mock.return_value.trigger_send.assert_called_with(
                'socorro_dev_test',
                fields
            )
            self.assertEqual(config.logger.error.call_count, 1)
            config.logger.error.assert_called_with(
                'Unable to send an email to %s, error is: %s',
                email, 'error', exc_info=True
            )

        list_service = exacttarget_mock.return_value.list.return_value
        list_service.get_subscriber.side_effect = (
            Exception(404, 'Bad Request')
        )

        exacttarget_mock.return_value.trigger_send.side_effect = (
            Exception(404, 'Bad Request')
        )

        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            email = 'fake@example.com'
            job.send_email({
                'processed_crash.email': email,
                'email_template': 'socorro_dev_test',
            })

            fields = {
                'EMAIL_ADDRESS_': 'fake@example.com',
                'EMAIL_FORMAT_': 'H',
                'TOKEN': 'fake@example.com'
            }
            exacttarget_mock.return_value.trigger_send.assert_called_with(
                'socorro_dev_test',
                fields
            )
            self.assertEqual(config.logger.error.call_count, 2)
            config.logger.error.assert_called_with(
                'Unable to send an email to %s, fields are %s, error is: %s',
                'fake@example.com',
                str(fields),
                "(404, 'Bad Request')",
                exc_info=True
            )

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_error_in_send_email_with_easy_correction(self, exacttarget_mock):
        attempted_emails = []

        def mocked_trigger_send(email_template, fields):
            attempted_emails.append(fields['EMAIL_ADDRESS_'])
            return True

        exacttarget_mock.return_value.trigger_send.side_effect = \
            mocked_trigger_send

        config_manager = self._setup_simple_config(
            common_email_domains=['example.com', 'gmail.com']
        )
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            email = 'fake@example.com'
            job.send_email({
                'processed_crash.email': email,
                'email_template': '',
            })

            self.assertEqual(config.logger.error.call_count, 0)

        # note that this means only one attempt was made
        self.assertEqual(attempted_emails, ['fake@example.com'])

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_error_in_send_email_with_clever_recovery(self, exacttarget_mock):
        attempted_emails = []

        def mocked_trigger_send(email_template, fields):
            attempted_emails.append(fields['EMAIL_ADDRESS_'])
            if fields['EMAIL_ADDRESS_'].endswith('exampl.com'):
                raise exacttarget.NewsletterException('error')
            else:
                return True

        exacttarget_mock.return_value.trigger_send.side_effect = \
            mocked_trigger_send

        config_manager = self._setup_simple_config(
            common_email_domains=['example.com', 'gmail.com']
        )
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            email = 'fake@exampl.com'
            job.send_email({
                'processed_crash.email': email,
                'email_template': '',
            })

            self.assertEqual(config.logger.error.call_count, 0)

        self.assertEqual(
            attempted_emails,
            ['fake@exampl.com', 'fake@example.com']
        )

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_error_in_send_email_recovery_failing(self, exacttarget_mock):
        attempted_emails = []

        def mocked_trigger_send(email_template, fields):
            # raise an error no matter what
            attempted_emails.append(fields['EMAIL_ADDRESS_'])
            raise exacttarget.NewsletterException('error')

        exacttarget_mock.return_value.trigger_send.side_effect = \
            mocked_trigger_send

        config_manager = self._setup_simple_config(
            common_email_domains=['example.com', 'gmail.com']
        )
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            email = 'fake@exampl.com'
            job.send_email({
                'processed_crash.email': email,
                'email_template': '',
            })

            self.assertEqual(config.logger.error.call_count, 1)
            config.logger.error.assert_called_with(
                'Unable to send a corrected email to %s, error is: %s',
                'fake@example.com', 'error', exc_info=True
            )

        self.assertEqual(
            attempted_emails,
            ['fake@exampl.com', 'fake@example.com']
        )

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_error_in_send_email_with_ambiguous_domain(self, exacttarget_mock):
        """try to send to a mail.com but let it fail.
        Because `mail.com` easily is spell corrected to `gmail.com` but
        we add `mail.com` as a common email domain in the config.
        """
        attempted_emails = []

        def mocked_trigger_send(email_template, fields):
            # raise an error no matter what
            attempted_emails.append(fields['EMAIL_ADDRESS_'])
            raise exacttarget.NewsletterException('error')

            if fields['EMAIL_ADDRESS_'].endswith('@mail.com.'):
                raise exacttarget.NewsletterException('error')
            else:
                return True

        exacttarget_mock.return_value.trigger_send.side_effect = \
            mocked_trigger_send

        config_manager = self._setup_simple_config(
            common_email_domains=['example.com', 'gmail.com', 'mail.com']
        )
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            email = 'banned@mail.com'
            job.send_email({
                'processed_crash.email': email,
                'email_template': '',
            })

            self.assertEqual(config.logger.error.call_count, 1)
            config.logger.error.assert_called_with(
                'Unable to send an email to %s, error is: %s',
                email, 'error', exc_info=True
            )

        self.assertEqual(
            attempted_emails,
            [email]
        )

    def test_update_user(self):
        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')
            now = utc_now().isoformat()

            es = SuperS().es(
                urls=config.elasticsearch.elasticsearch_urls,
                timeout=config.elasticsearch.elasticsearch_timeout,
            )
            search = es.indexes(
                config.elasticsearch.elasticsearch_emails_index
            )
            search = search.doctypes('emails')

            connection = es.get_es()

            job.update_user('someone@example.com', now, connection)
            connection.refresh()

            s = search.filter(_id='someone@example.com')
            res = list(s.values_list('last_sending'))

            self.assertEqual(len(res), 1)
            self.assertEqual(res[0][0], now)

            # Test with a non-existing user
            job.update_user('idonotexist@example.com', now, connection)
            connection.refresh()

            s = search.filter(_id='idonotexist@example.com')
            res = list(s.values_list('last_sending'))

            self.assertEqual(len(res), 1)
            self.assertEqual(res[0][0], now)

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_email_cannot_be_sent_twice(self, exacttarget_mock):
        config_manager = self._setup_config_manager(
            restrict_products=['NightlyTrain']
        )
        et_mock = exacttarget_mock.return_value

        # Prepare failures
        _failures = []
        _email_sent = []

        class SomeRandomError(Exception):
            pass

        def trigger_send(template, fields):
            email = fields['EMAIL_ADDRESS_']
            if email == 'c@example.org' and email not in _failures:
                _failures.append(email)
                raise SomeRandomError('This is an error. ')
            else:
                _email_sent.append(email)

        et_mock.trigger_send = trigger_send

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['automatic-emails']
            assert information['automatic-emails']['last_error']
            self.assertEqual(
                information['automatic-emails']['last_error']['type'],
                str(SomeRandomError)
            )

            # Verify that user's data was updated, but not all of it
            self.assertEqual(_email_sent, ['a@example.org', 'b@example.org'])
            emails_list = (
                'a@example.org',
                'b@example.org',
                'c@example.org',
                'd@example.org',
                'e@example.org'
            )

            conf = config.crontabber['class-AutomaticEmailsCronApp']
            es = SuperS().es(
                urls=conf.elasticsearch.elasticsearch_urls,
                timeout=conf.elasticsearch.elasticsearch_timeout,
            )
            search = es.indexes(
                conf.elasticsearch.elasticsearch_emails_index
            )
            search = search.doctypes('emails')
            es.get_es().refresh()

            search = search.filter(_id__in=emails_list)
            res = search.execute()
            self.assertEqual(res.count, 2)

            now = utc_now()
            for row in res.results:
                assert row['_id'] in ('a@example.org', 'b@example.org')
                date = string_to_datetime(row['_source']['last_sending'])
                self.assertEqual(date.year, now.year)
                self.assertEqual(date.month, now.month)
                self.assertEqual(date.day, now.day)

            # Run crontabber again and verify that all users are updated,
            # and emails are not sent twice
            state = tab.database['automatic-emails']
            self._wind_clock(state, hours=1)
            tab.database['automatic-emails'] = state

            tab.run_all()

            information = self._load_structure()
            assert information['automatic-emails']
            assert not information['automatic-emails']['last_error']
            assert information['automatic-emails']['last_success']

            # Verify that users were not sent an email twice
            self.assertEqual(_email_sent, [
                'a@example.org',
                'b@example.org',
                'c@example.org',
                'd@example.org',
                'e@example.org'
            ])

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_email_after_delay(self, exacttarget_mock):
        """Test that a user will receive an email if he or she sends us a new
        crash report after the delay is passed (but not before). """
        config_manager = self._setup_config_manager(
            delay_between_emails=1,
            restrict_products=['EarthRaccoon']
        )
        email = 'me@my.name'
        list_service_mock = exacttarget_mock.return_value.list.return_value
        list_service_mock.get_subscriber.return_value = {
            'token': email
        }
        trigger_send_mock = exacttarget_mock.return_value.trigger_send
        tomorrow = utc_now() + datetime.timedelta(days=1, hours=2)
        twohourslater = utc_now() + datetime.timedelta(hours=2)

        storage_config_manager = self._setup_storage_config()
        with storage_config_manager.context() as storage_config:
            storage = ElasticSearchCrashStorage(storage_config)

        with config_manager.context() as config:
            # 1. Send an email to the user and update emailing data
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['automatic-emails']
            assert not information['automatic-emails']['last_error']
            assert information['automatic-emails']['last_success']

            exacttarget_mock.return_value.trigger_send.assert_called_with(
                'socorro_dev_test',
                {
                    'EMAIL_ADDRESS_': email,
                    'EMAIL_FORMAT_': 'H',
                    'TOKEN': email
                }
            )
            self.assertEqual(trigger_send_mock.call_count, 1)

            # 2. Test that before 'delay' is passed user doesn't receive
            # another email

            # Insert a new crash report with the same email address
            storage.save_processed({
                'uuid': '50',
                'email': email,
                'product': 'EarthRaccoon',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': utc_now() + datetime.timedelta(hours=1)
            })
            storage.es.refresh()

            # Run crontabber with time pushed by two hours
            with mock.patch('socorro.cron.crontabber.utc_now') as cronutc_mock:
                with mock.patch('socorro.cron.base.utc_now') as baseutc_mock:
                    cronutc_mock.return_value = twohourslater
                    baseutc_mock.return_value = twohourslater
                    tab.run_all()

            information = self._load_structure()
            assert information['automatic-emails']
            assert not information['automatic-emails']['last_error']
            assert information['automatic-emails']['last_success']

            # No new email was sent
            self.assertEqual(trigger_send_mock.call_count, 1)

            # 3. Verify that, after 'delay' is passed, a new email is sent
            # to our user

            # Insert a new crash report with the same email address
            storage.save_processed({
                'uuid': '51',
                'email': email,
                'product': 'EarthRaccoon',
                'version': '20.0',
                'release_channel': 'Release',
                'date_processed': utc_now() + datetime.timedelta(days=1)
            })
            storage.es.refresh()

            # Run crontabber with time pushed by a day
            with mock.patch('socorro.cron.crontabber.utc_now') as cronutc_mock:
                with mock.patch('socorro.cron.base.utc_now') as baseutc_mock:
                    cronutc_mock.return_value = tomorrow
                    baseutc_mock.return_value = tomorrow
                    tab.run_all()

            information = self._load_structure()
            assert information['automatic-emails']
            assert not information['automatic-emails']['last_error']
            assert information['automatic-emails']['last_success']

            # A new email was sent
            self.assertEqual(trigger_send_mock.call_count, 2)
