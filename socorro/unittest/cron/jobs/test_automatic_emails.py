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
from ..base import IntegrationTestCaseBase


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
                'someoneelse@example.com',
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

        cursor.execute("""
            INSERT INTO emails (email, last_sending)
            VALUES (
                'someone@example.com',
                '%(last_month)s'
            ), (
                'someoneelse@example.com',
                '%(last_month)s'
            ), (
                'anotherone@example.com',
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

    def _setup_simple_config(self):
        return ConfigurationManager(
            [automatic_emails.AutomaticEmailsCronApp.get_required_config()],
            values_source_list=[{
                'delay_between_emails': 7,
                'exacttarget_user': '',
                'exacttarget_password': '',
                'restrict_products': ['WaterWolf'],
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
            self.assertEqual(et_mock.trigger_send.call_count, 3)

            # Verify the last call to trigger_send
            fields = {
                'EMAIL_ADDRESS_': 'anotherone@example.com',
                'EMAIL_FORMAT_': 'H',
                'TOKEN': 'anotherone@example.com'
            }

            et_mock.trigger_send.assert_called_with('socorro_dev_test', fields)

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_run(self, exacttarget_mock):
        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')
            job.run(self.conn, utc_now())

            et_mock = exacttarget_mock.return_value
            self.assertEqual(et_mock.trigger_send.call_count, 3)

    @mock.patch('socorro.external.exacttarget.exacttarget.ExactTarget')
    def test_send_email(self, exacttarget_mock):
        list_service_mock = exacttarget_mock.return_value.list.return_value
        subscriber = list_service_mock.get_subscriber.return_value
        subscriber.SubscriberKey = 'fake@example.com'

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

    def test_update_user(self):
        config_manager = self._setup_simple_config()
        with config_manager.context() as config:
            job = automatic_emails.AutomaticEmailsCronApp(config, '')

            report = {
                'email': 'someone@example.com'
            }
            now = utc_now()
            job.update_user(report, now, self.conn)

            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT last_sending FROM emails WHERE email=%(email)s
            """, report)

            self.assertEqual(cursor.rowcount, 1)
            row = cursor.fetchone()
            self.assertEqual(row[0], now)
