# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import mock
from nose.plugins.attrib import attr

from configman import ConfigurationManager

from socorro.cron import crontabber
from socorro.cron.jobs import automatic_emails
from socorro.external.exacttarget import exacttarget
from socorro.lib.datetimeutil import utc_now
from ..base import IntegrationTestCaseBase, TestCaseBase


#==============================================================================
class TestAutomaticEmails(TestCaseBase):

    def _setup_simple_config(self, domains=None):
        conf = automatic_emails.AutomaticEmailsCronApp.get_required_config()
        conf.add_option('logger', default=mock.Mock())

        return ConfigurationManager(
            [conf],
            values_source_list=[{
                'common_email_domains': domains,
            }]
        )

    def test_correct_email(self):
        domains = ('gmail.com', 'yahoo.com')
        config_manager = self._setup_simple_config(domains=domains)
        with config_manager.context() as config:
            app = automatic_emails.AutomaticEmailsCronApp(config, '')
            # easy corrections
            self.assertEqual(
                app.correct_email('peterbe@YAHOOO.COM'),
                'peterbe@yahoo.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@gmai.com'),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@gmaill.com'),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                # case insensitive
                app.correct_email('peterbe@Gamil.com'),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@gmaiK.com'),
                'peterbe@gmail.com'
            )
            self.assertEqual(
                app.correct_email('peterbe@gmail..com'),
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
                app.correct_email('peterbe@Gamil.com.'),
                'peterbe@gmail.com'
            )

            # What doesn't work are edit distances greater than 1
            self.assertFalse(app.correct_email('peterbe@gamill.com'))
            self.assertFalse(app.correct_email('peterbe@gmil.cam'))
            # and don't mess with @ signs
            self.assertFalse(
                app.correct_email('peterbe@hotmail.com@gamil.com')
            )


#==============================================================================
@attr(integration='postgres')  # for nosetests
class TestFunctionalAutomaticEmails(IntegrationTestCaseBase):

    def setUp(self):
        super(TestFunctionalAutomaticEmails, self).setUp()
        # prep a fake table
        now = utc_now() - datetime.timedelta(minutes=30)
        last_month = now - datetime.timedelta(days=31)
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO reports
            (uuid, email, product, version, release_channel, date_processed)
            VALUES (
                '1',
                'someone@example.com',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            ), (
                '2',
                '"Quidam" <quidam@example.com>',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            ), (
                '3',
                'anotherone@example.com',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            ), (
                '4',
                'a@example.org',
                'NightlyTrain',
                '1.0',
                'Nightly',
                '%(now)s'
            ), (
                '5',
                'b@example.org',
                'NightlyTrain',
                '1.0',
                'Nightly',
                '%(now)s'
            ), (
                '6',
                'c@example.org',
                'NightlyTrain',
                '1.0',
                'Nightly',
                '%(now)s'
            ), (
                '7',
                'd@example.org',
                'NightlyTrain',
                '1.0',
                'Nightly',
                '%(now)s'
            ), (
                '8',
                'e@example.org',
                'NightlyTrain',
                '1.0',
                'Nightly',
                '%(now)s'
            ), (
                '9',
                'me@my.name',
                'EarthRaccoon',
                '1.0',
                'Nightly',
                '%(now)s'
            ), (
                '18',
                'z\xc3\x80drian@example.org',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            )
        """ % {'now': now})

        # Let's insert a duplicate
        cursor.execute("""
            INSERT INTO reports
            (uuid, email, product, version, release_channel, date_processed)
            VALUES (
                '10',
                'anotherone@example.com',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            )
        """ % {'now': now})

        # And let's insert some invalid crashes
        cursor.execute("""
            INSERT INTO reports
            (uuid, email, product, version, release_channel, date_processed)
            VALUES (
                '11',
                null,
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            ), (
                '12',
                'myemail@example.com',
                'WaterWolf',
                '20.0',
                'Release',
                '%(last_month)s'
            ), (
                '13',
                'menime@example.com',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            ), (
                '14',
                'hi@mynameis.slim',
                'WindBear',
                '20.0',
                'Release',
                '%(now)s'
            )
        """ % {'now': now, 'last_month': last_month})

        # Finally some invalid email addresses
        cursor.execute("""
            INSERT INTO reports
            (uuid, email, product, version, release_channel, date_processed)
            VALUES (
                '15',
                '     ',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            ), (
                '16',
                'invalid@email',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            ), (
                '17',
                'i.do.not.work',
                'WaterWolf',
                '20.0',
                'Release',
                '%(now)s'
            )
        """ % {'now': now})

        cursor.execute("""
            INSERT INTO emails (email, last_sending)
            VALUES (
                'someone@example.com',
                '%(last_month)s'
            ), (
                '"Quidam" <quidam@example.com>',
                '%(last_month)s'
            ), (
                'menime@example.com',
                '%(now)s'
            )
        """ % {'now': now, 'last_month': last_month})

        self.conn.commit()

    def tearDown(self):
        super(TestFunctionalAutomaticEmails, self).tearDown()
        self.conn.cursor().execute("""
            TRUNCATE TABLE reports, emails CASCADE;
        """)
        self.conn.commit()

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
        }

        config_manager, json_file = super(
            TestFunctionalAutomaticEmails,
            self
        )._setup_config_manager(
            'socorro.cron.jobs.automatic_emails.AutomaticEmailsCronApp|1h',
            extra_value_source=extra_value_source
        )
        return config_manager, json_file

    def _setup_simple_config(self, common_email_domains=None):
        conf = automatic_emails.AutomaticEmailsCronApp.get_required_config()
        conf.add_option('logger', default=mock.Mock())

        values_source_list = {
            'delay_between_emails': 7,
            'exacttarget_user': '',
            'exacttarget_password': '',
            'restrict_products': ['WaterWolf'],
            'email_template': 'socorro_dev_test'
        }
        if common_email_domains:
            values_source_list['common_email_domains'] = common_email_domains
        return ConfigurationManager(
            [conf],
            values_source_list=[values_source_list]
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
                'email_template': 'socorro_dev_test'
            }]
        )

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_cron_job(self, exacttarget_mock):
        (config_manager, json_file) = self._setup_config_manager()
        et_mock = exacttarget_mock.return_value

        # Make get_subscriber raise an exception
        list_service = et_mock.list.return_value = mock.Mock()
        list_service.get_subscriber = mock.Mock(
            side_effect=exacttarget.NewsletterException()
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
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
            cursor = self.conn.cursor()
            emails_list = (
                'someone@example.com',
                '"Quidam" <quidam@example.com>',
                'anotherone@example.com'
            )
            sql = """
                SELECT last_sending
                FROM emails
                WHERE email IN %s
            """ % (emails_list,)
            cursor.execute(sql)
            self.assertEqual(cursor.rowcount, 3)
            now = utc_now()
            for row in cursor.fetchall():
                self.assertEqual(row[0].year, now.year)
                self.assertEqual(row[0].month, now.month)
                self.assertEqual(row[0].day, now.day)

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_run(self, exacttarget_mock):
        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')
            job.run(self.conn, utc_now())

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

            report = {
                'email': 'fake@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
            }
            job.send_email(report)

            fields = {
                'EMAIL_ADDRESS_': report['email'],
                'EMAIL_FORMAT_': 'H',
                'TOKEN': report['email']
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

            report = {
                'email': 'fake@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
            }
            job.send_email(report)

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

            report = {
                'email': 'fake@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
            }
            job.send_email(report)

            fields = {
                'EMAIL_ADDRESS_': 'fake@example.com',
                'EMAIL_FORMAT_': 'H',
                'TOKEN': 'fake@example.com'
            }
            exacttarget_mock.return_value.trigger_send.assert_called_with(
                'socorro_dev_test',
                fields
            )
            self.assertEqual(config.logger.error.call_count, 1)
            config.logger.error.assert_called_with(
                'Unable to send an email to %s, error is: %s',
                'fake@example.com', 'error', exc_info=True
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

            report = {
                'email': 'fake@example.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
            }
            job.send_email(report)

            fields = {
                'EMAIL_ADDRESS_': u'fake@example.com',
                'EMAIL_FORMAT_': 'H',
                'TOKEN': u'fake@example.com'
            }
            exacttarget_mock.return_value.trigger_send.assert_called_with(
                'socorro_dev_test',
                fields
            )
            self.assertEqual(config.logger.error.call_count, 2)
            config.logger.error.assert_called_with(
                'Unable to send an email to %s, fields are %s, error is: %s',
                u'fake@example.com',
                str(fields),
                "(404, 'Bad Request')",
                exc_info=True
            )

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_error_in_send_email_with_recovery(self, exacttarget_mock):
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

            report = {
                'email': 'fake@exampl.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
            }
            job.send_email(report)

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

            report = {
                'email': 'fake@exampl.com',
                'product': 'WaterWolf',
                'version': '20.0',
                'release_channel': 'Release',
            }
            job.send_email(report)

            self.assertEqual(config.logger.error.call_count, 1)
            config.logger.error.assert_called_with(
                'Unable to send a corrected email to %s, error is: %s',
                'fake@example.com', 'error', exc_info=True
            )

        self.assertEqual(
            attempted_emails,
            ['fake@exampl.com', 'fake@example.com']
        )

    def test_update_user(self):
        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')
            now = utc_now()

            report = {
                'email': 'someone@example.com'
            }
            job.update_user(report, now, self.conn)

            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT last_sending FROM emails WHERE email=%(email)s
            """, report)

            self.assertEqual(cursor.rowcount, 1)
            row = cursor.fetchone()
            self.assertEqual(row[0], now)

            # Test with a non-existing user
            report = {
                'email': 'idonotexist@example.com'
            }
            job.update_user(report, now, self.conn)

            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT last_sending FROM emails WHERE email=%(email)s
            """, report)

            self.assertEqual(cursor.rowcount, 1)
            row = cursor.fetchone()
            self.assertEqual(row[0], now)

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_email_cannot_be_sent_twice(self, exacttarget_mock):
        (config_manager, json_file) = self._setup_config_manager(
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

            information = json.load(open(json_file))
            assert information['automatic-emails']
            assert information['automatic-emails']['last_error']
            self.assertEqual(
                information['automatic-emails']['last_error']['type'],
                str(SomeRandomError)
            )

            # Verify that user's data was updated, but not all of it
            self.assertEqual(_email_sent, ['a@example.org', 'b@example.org'])
            cursor = self.conn.cursor()
            emails_list = (
                'a@example.org',
                'b@example.org',
                'c@example.org',
                'd@example.org',
                'e@example.org'
            )
            sql = """
                SELECT email, last_sending
                FROM emails
                WHERE email IN %s
            """ % (emails_list,)
            cursor.execute(sql)
            now = utc_now()
            self.assertEqual(cursor.rowcount, 2)
            for row in cursor.fetchall():
                assert row[0] in ('a@example.org', 'b@example.org')
                self.assertEqual(row[1].year, now.year)
                self.assertEqual(row[1].month, now.month)
                self.assertEqual(row[1].day, now.day)

            # Run crontabber again and verify that all users are updated,
            # and emails are not sent twice
            self._wind_clock(json_file, hours=1)

            # This forces a crontabber instance to reload the JSON file
            tab._database = None

            tab.run_all()

            information = json.load(open(json_file))
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
        (config_manager, json_file) = self._setup_config_manager(
            delay_between_emails=1,
            restrict_products=['EarthRaccoon']
        )
        list_service_mock = exacttarget_mock.return_value.list.return_value
        list_service_mock.get_subscriber.return_value = {
            'token': 'me@my.name'
        }
        trigger_send_mock = exacttarget_mock.return_value.trigger_send
        tomorrow = utc_now() + datetime.timedelta(days=1, hours=2)
        twohourslater = utc_now() + datetime.timedelta(hours=2)

        with config_manager.context() as config:
            # 1. Send an email to the user and update emailing data
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['automatic-emails']
            assert not information['automatic-emails']['last_error']
            assert information['automatic-emails']['last_success']

            exacttarget_mock.return_value.trigger_send.assert_called_with(
                'socorro_dev_test',
                {
                    'EMAIL_ADDRESS_': 'me@my.name',
                    'EMAIL_FORMAT_': 'H',
                    'TOKEN': 'me@my.name'
                }
            )
            self.assertEqual(trigger_send_mock.call_count, 1)

            # 2. Test that before 'delay' is passed user doesn't receive
            # another email

            # Insert a new crash report with the same email address
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO reports
                (uuid, email, product, version, release_channel, date_processed)
                VALUES (
                    '50',
                    'me@my.name',
                    'EarthRaccoon',
                    '20.0',
                    'Release',
                    '%(onehourlater)s'
                )
            """ % {'onehourlater': utc_now() + datetime.timedelta(hours=1)})
            self.conn.commit()

            # Run crontabber with time pushed by two hours
            with mock.patch('socorro.cron.crontabber.utc_now') as cronutc_mock:
                with mock.patch('socorro.cron.base.utc_now') as baseutc_mock:
                    cronutc_mock.return_value = twohourslater
                    baseutc_mock.return_value = twohourslater
                    tab.run_all()

            information = json.load(open(json_file))
            assert information['automatic-emails']
            assert not information['automatic-emails']['last_error']
            assert information['automatic-emails']['last_success']

            # No new email was sent
            self.assertEqual(trigger_send_mock.call_count, 1)

            # 3. Verify that, after 'delay' is passed, a new email is sent
            # to our user

            # Insert a new crash report with the same email address
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO reports
                (uuid, email, product, version, release_channel, date_processed)
                VALUES (
                    '51',
                    'me@my.name',
                    'EarthRaccoon',
                    '20.0',
                    'Release',
                    '%(tomorrow)s'
                )
            """ % {'tomorrow': utc_now() + datetime.timedelta(days=1)})
            self.conn.commit()

            # Run crontabber with time pushed by a day
            with mock.patch('socorro.cron.crontabber.utc_now') as cronutc_mock:
                with mock.patch('socorro.cron.base.utc_now') as baseutc_mock:
                    cronutc_mock.return_value = tomorrow
                    baseutc_mock.return_value = tomorrow
                    tab.run_all()

            information = json.load(open(json_file))
            assert information['automatic-emails']
            assert not information['automatic-emails']['last_error']
            assert information['automatic-emails']['last_success']

            # A new email was sent
            self.assertEqual(trigger_send_mock.call_count, 2)
