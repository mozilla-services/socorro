# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock

from datetime import datetime, timedelta

from configman import ConfigurationManager

from socorro.processor.registration_client import (
  ProcessorAppRegistrationClient,
  RegistrationError
)
from socorro.external.postgresql.dbapi2_util import SQLDidNotReturnSingleValue
from socorro.lib.datetimeutil import UTC

def sequencer(*args):
    active_iter = iter(args)

    def foo(*args, **kwargs):
        try:
            value = active_iter.next()
        except StopIteration:
            raise Exception('out of values')
        if isinstance(value, Exception):
            raise value
        return value
    return foo


class TestProcessorAppRegistrationAgent(unittest.TestCase):

    def test_basic_setup(self):
        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres
          }]
        )
        m_registration = mock.Mock()

        class NoRegister(ProcessorAppRegistrationClient):
            _registration = m_registration

        with config_manager.context() as config:
            registrar = NoRegister(config)
            self.assertEqual(registrar.last_checkin_ts,
                             datetime(1999, 1, 1, tzinfo=UTC))
            self.assertTrue(registrar.processor_id is None)
            self.assertEqual(registrar.processor_name, 'unknown')
            self.assertEqual(m_registration.call_count, 1)

    def test_checkin_done(self):
        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres
          }]
        )
        m_registration = mock.Mock()

        class NoRegister(ProcessorAppRegistrationClient):
            _registration = m_registration

        with config_manager.context() as config:
            registrar = NoRegister(config)

            utc_now_mock_str = 'socorro.processor.registration_client.utc_now'
            with mock.patch(utc_now_mock_str) as m_utc_now:
                a_date = datetime(year=2012,
                                  month=5,
                                  day=4,
                                  hour=15,
                                  minute=10,
                                  tzinfo=UTC)
                m_utc_now.return_value = a_date
                m_database = mock.MagicMock()
                m_database.__enter__.return_value = m_database
                m_connection = m_database
                registrar.database.return_value = m_database
                registrar.processor_id = 17

                m_cursor = mock.Mock()
                m_connection.cursor.return_value = m_cursor
                m_execute = mock.Mock()
                m_cursor.execute = m_execute

                registrar.checkin()

                m_execute.assert_called_once_with(
                  "update processors set lastseendatetime = %s where id = %s",
                  (a_date, 17)
                )

    def test_checkin_not_necessary(self):
        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres
          }]
        )
        m_registration = mock.Mock()

        class NoRegister(ProcessorAppRegistrationClient):
            _registration = m_registration

        with config_manager.context() as config:
            registrar = NoRegister(config)

            utc_now_mock_str = 'socorro.processor.registration_client.utc_now'
            with mock.patch(utc_now_mock_str) as m_utc_now:
                a_date = datetime(year=1999,
                                  month=1,
                                  day=1,
                                  hour=0,
                                  minute=2,
                                  tzinfo=UTC)
                m_utc_now.return_value = a_date
                m_database = mock.MagicMock()
                m_database.__enter__.return_value = m_database
                m_connection = m_database
                registrar.database.return_value = m_database
                registrar.processor_id = 17

                m_cursor = mock.Mock()
                m_connection.cursor.return_value = m_cursor
                m_execute = mock.Mock()
                m_cursor.execute = m_execute

                registrar.checkin()

                self.assertEqual(m_execute.call_count, 0)

    def test_requested_processor_id(self):
        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres
          }]
        )
        m_registration = mock.Mock()

        class NoRegister(ProcessorAppRegistrationClient):
            _registration = m_registration

        with config_manager.context() as config:
            registrar = NoRegister(config)
            i = registrar._requested_processor_id(0)
            self.assertEqual(i, 0)
            i = registrar._requested_processor_id(1)
            self.assertEqual(1, i)
            i = registrar._requested_processor_id('host')
            self.assertEqual('host', i)
            i = registrar._requested_processor_id('auto')
            self.assertEqual('auto', i)
            self.assertRaises(ValueError,
                              registrar._requested_processor_id,
                              'dwight')

    def test_select_host_mode_success(self):
        a_date = datetime(year=2012,
                          month=5,
                          day=4,
                          hour=15,
                          minute=10,
                          tzinfo=UTC)
        frequency = timedelta(0, 300)
        threshold = a_date - frequency

        mock_logging = mock.Mock()
        mock_connection = mock.MagicMock()
        mock_postgres = mock.MagicMock(return_value=mock_connection)
        mock_connection.return_value = mock_connection
        mock_connection.__enter__.return_value = mock_connection
        mock_cursor = mock.Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_execute = mock.Mock()
        mock_cursor.execute = mock_execute
        fetchall_returns = sequencer(((threshold,),), ((17,),))
        mock_fetchall = mock.Mock(side_effect=fetchall_returns)
        mock_cursor.fetchall = mock_fetchall
        mock_fetchone = mock.Mock()
        mock_cursor.fetchone = mock_fetchone

        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres,
            'processor_id': 'host',
          }]
        )
        with config_manager.context() as config:
            mock_os_uname_str = 'os.uname'
            with mock.patch(mock_os_uname_str) as mock_uname:
                mock_uname.return_value = (0, 'dwight.wilma.sarita')

                registrar = ProcessorAppRegistrationClient(config)
                name = registrar.processor_name
                # There should be 1 and only 1 occurance of a '.' in the name
                self.assertEqual(name.find('.'), name.rfind('.'))

                self.assertEqual(mock_execute.call_count, 4)

                expected_execute_args = (
                    (("select now() - interval %s", (frequency,)),),
                    ((("select id from processors"
                       " where lastseendatetime < %s"
                       " and name like %s limit 1"),
                      (threshold, 'dwight_wilma_sarita%')),),
                    ((("update processors set name = %s, "
                       "startdatetime = now(), lastseendatetime = now()"
                       " where id = %s"), (name, 17)),),
                    ((("update jobs set"
                       "    starteddatetime = NULL,"
                       "    completeddatetime = NULL,"
                       "    success = NULL "
                       "where"
                       "    owner = %s"), (17,)),),
                )
                actual_execute_args = mock_execute.call_args_list
                for expected, actual in zip(expected_execute_args,
                                            actual_execute_args):
                    self.assertEqual(expected, actual)

    def test_select_forcehost_mode_success(self):
        a_date = datetime(year=2012,
                          month=5,
                          day=4,
                          hour=15,
                          minute=10,
                          tzinfo=UTC)
        frequency = timedelta(0, 300)
        threshold = a_date - frequency

        mock_logging = mock.Mock()
        mock_connection = mock.MagicMock()
        mock_postgres = mock.MagicMock(return_value=mock_connection)
        mock_connection.return_value = mock_connection
        mock_connection.__enter__.return_value = mock_connection
        mock_cursor = mock.Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_execute = mock.Mock()
        mock_cursor.execute = mock_execute
        fetchall_returns = sequencer(((threshold,),), ((17,),))
        mock_fetchall = mock.Mock(side_effect=fetchall_returns)
        mock_cursor.fetchall = mock_fetchall
        mock_fetchone = mock.Mock()
        mock_cursor.fetchone = mock_fetchone

        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres,
            'processor_id': 'forcehost',
          }]
        )
        with config_manager.context() as config:
            mock_os_uname_str = 'os.uname'
            with mock.patch(mock_os_uname_str) as mock_uname:
                mock_uname.return_value = (0, 'wilma')

                registrar = ProcessorAppRegistrationClient(config)
                name = registrar.processor_name

                self.assertEqual(mock_execute.call_count, 4)

                expected_execute_args = (
                    (("select now() - interval %s", (frequency,)),),
                    ((("select id from processors"
                       " where name like %s limit 1"), ('wilma%',)),),
                    ((("update processors set name = %s, "
                       "startdatetime = now(), lastseendatetime = now()"
                       " where id = %s"), (name, 17)),),
                    ((("update jobs set"
                       "    starteddatetime = NULL,"
                       "    completeddatetime = NULL,"
                       "    success = NULL "
                       "where"
                       "    owner = %s"), (17,)),),
                )
                actual_execute_args = mock_execute.call_args_list
                for expected, actual in zip(expected_execute_args,
                                            actual_execute_args):
                    self.assertEqual(expected, actual)

    def test_select_host_mode_not_found_start_new(self):
        a_date = datetime(year=2012,
                          month=5,
                          day=4,
                          hour=15,
                          minute=10,
                          tzinfo=UTC)
        frequency = timedelta(0, 300)
        threshold = a_date - frequency

        mock_logging = mock.Mock()
        mock_connection = mock.MagicMock()
        mock_postgres = mock.MagicMock(return_value=mock_connection)
        mock_connection.return_value = mock_connection
        mock_connection.__enter__.return_value = mock_connection
        mock_cursor = mock.Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_execute = mock.Mock()
        mock_cursor.execute = mock_execute
        fetchall_returns = sequencer(((threshold,),),
                                     SQLDidNotReturnSingleValue(),
                                     SQLDidNotReturnSingleValue(),
                                     ((92,),),)
        mock_fetchall = mock.Mock(side_effect=fetchall_returns)
        mock_cursor.fetchall = mock_fetchall
        mock_fetchone = mock.Mock()
        mock_cursor.fetchone = mock_fetchone

        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres,
            'processor_id': 'host',
          }]
        )
        with config_manager.context() as config:
            mock_os_uname_str = 'os.uname'
            with mock.patch(mock_os_uname_str) as mock_uname:
                mock_uname.return_value = (0, 'wilma')

                registrar = ProcessorAppRegistrationClient(config)
                name = registrar.processor_name

                self.assertEqual(mock_execute.call_count, 4)

                expected_execute_args = (
                    (("select now() - interval %s", (frequency,)),),
                    ((("select id from processors"
                       " where lastseendatetime < %s"
                       " and name like %s limit 1"), (threshold, 'wilma%')),),
                    ((("select id from processors"
                       " where name like 'wilma%'"), None),),
                    ((("insert into processors"
                       "    (id,"
                       "     name,"
                       "     startdatetime,"
                       "     lastseendatetime) "
                       "values"
                       "    (default,"
                       "     %s,"
                       "     now(),"
                       "     now()) "
                       "returning id"), (name,)),),
                )
                actual_execute_args = mock_execute.call_args_list
                for expected, actual in zip(expected_execute_args,
                                            actual_execute_args):
                    self.assertEqual(expected, actual)

    def test_select_forcehost_mode_not_found_start_new(self):
        a_date = datetime(year=2012,
                          month=5,
                          day=4,
                          hour=15,
                          minute=10,
                          tzinfo=UTC)
        frequency = timedelta(0, 300)
        threshold = a_date - frequency

        mock_logging = mock.Mock()
        mock_connection = mock.MagicMock()
        mock_postgres = mock.MagicMock(return_value=mock_connection)
        mock_connection.return_value = mock_connection
        mock_connection.__enter__.return_value = mock_connection
        mock_cursor = mock.Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_execute = mock.Mock()
        mock_cursor.execute = mock_execute
        fetchall_returns = sequencer(((threshold,),),
                                     SQLDidNotReturnSingleValue(),
                                     ((92,),),)
        mock_fetchall = mock.Mock(side_effect=fetchall_returns)
        mock_cursor.fetchall = mock_fetchall
        mock_fetchone = mock.Mock()
        mock_cursor.fetchone = mock_fetchone

        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres,
            'processor_id': 'forcehost',
          }]
        )
        with config_manager.context() as config:
            mock_os_uname_str = 'os.uname'
            with mock.patch(mock_os_uname_str) as mock_uname:
                mock_uname.return_value = (0, 'wilma')

                registrar = ProcessorAppRegistrationClient(config)
                name = registrar.processor_name

                self.assertEqual(mock_execute.call_count, 3)

                expected_execute_args = (
                    (("select now() - interval %s", (frequency,)),),
                    ((("select id from processors"
                       " where name like %s limit 1"), ('wilma%',)),),
                    ((("insert into processors"
                       "    (id,"
                       "     name,"
                       "     startdatetime,"
                       "     lastseendatetime) "
                       "values"
                       "    (default,"
                       "     %s,"
                       "     now(),"
                       "     now()) "
                       "returning id"), (name,)),),
                )
                actual_execute_args = mock_execute.call_args_list
                for expected, actual in zip(expected_execute_args,
                                            actual_execute_args):
                    self.assertEqual(expected, actual)

    def test_select_host_mode_not_dead_fail(self):
        a_date = datetime(year=2012,
                          month=5,
                          day=4,
                          hour=15,
                          minute=10,
                          tzinfo=UTC)
        frequency = timedelta(0, 300)
        threshold = a_date - frequency

        mock_logging = mock.Mock()
        mock_connection = mock.MagicMock()
        mock_postgres = mock.MagicMock(return_value=mock_connection)
        mock_connection.return_value = mock_connection
        mock_connection.__enter__.return_value = mock_connection
        mock_cursor = mock.Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_execute = mock.Mock()
        mock_cursor.execute = mock_execute
        fetchall_returns = sequencer(((threshold,),),
                                     SQLDidNotReturnSingleValue(),
                                     ((92,),),)
        mock_fetchall = mock.Mock(side_effect=fetchall_returns)
        mock_cursor.fetchall = mock_fetchall
        mock_fetchone = mock.Mock()
        mock_cursor.fetchone = mock_fetchone

        required_config = ProcessorAppRegistrationClient.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres,
            'processor_id': 'host',
          }]
        )
        with config_manager.context() as config:
            mock_os_uname_str = 'os.uname'
            with mock.patch(mock_os_uname_str) as mock_uname:
                mock_uname.return_value = (0, 'wilma')

                self.assertRaises(RegistrationError,
                                  ProcessorAppRegistrationClient,
                                  config)

                self.assertEqual(mock_execute.call_count, 3)

                expected_execute_args = (
                    (("select now() - interval %s", (frequency,)),),
                    ((("select id from processors"
                       " where lastseendatetime < %s"
                       " and name like %s limit 1"), (threshold, 'wilma%')),),
                    ((("select id from processors"
                       " where name like 'wilma%'"), None),),
                )
                actual_execute_args = mock_execute.call_args_list
                for expected, actual in zip(expected_execute_args,
                                            actual_execute_args):
                    self.assertEqual(expected, actual)
