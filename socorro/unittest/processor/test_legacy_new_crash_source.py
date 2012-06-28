import unittest
import mock

from configman.dotdict import DotDict

from socorro.processor.legacy_new_crash_source import (
  LegacyNewCrashSource,
)
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
    single_value_sql
)

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

class TestLegacyNewCrashSource(unittest.TestCase):
    """
    """

    def test_legacy_new_crash_source_basics(self):
        m_transaction_executor_class = mock.Mock()

        config = DotDict()
        database = mock.Mock()
        config.database_class = mock.Mock(return_value=database)
        config.transaction_executor_class = m_transaction_executor_class
        config.batchJobLimit = 10

        new_crash_source = LegacyNewCrashSource(config,
                                       processor_name='dwight-1234')

        self.assertEqual(m_transaction_executor_class.call_count, 1)
        m_transaction_executor_class.assert_called_with(
          config,
          database,
          None)

    def test_incoming_job_stream_normal(self):
        config = DotDict()
        config.database_class = mock.Mock()
        config.transaction_executor_class = mock.Mock()
        config.batchJobLimit = 10
        config.logger = mock.Mock()

        class StubbedIterators(LegacyNewCrashSource):
            def _priority_jobs_iter(self):
                while True:
                    yield None

            def _normal_jobs_iter(self):
                values = [
                    (1, '1234', 1),
                    (2, '2345', 1),
                    (3, '3456', 1),
                    (4, '4567', 1),
                    (5, '5678', 1),
                ]
                for x in values:
                    yield x

        new_crash_source = StubbedIterators(config,
                                       processor_name='sherman1234')
        expected = ('1234',
                    '2345',
                    '3456',
                    '4567',
                    '5678',
                   )
        for x, y in zip(new_crash_source, expected):
            self.assertEqual(x, y)

        self.assertEqual(len([x for x in new_crash_source]), 5)


    def test_incoming_job_stream_priority(self):
        config = DotDict()
        config.database_class = mock.Mock()
        config.transaction_executor_class = mock.Mock()
        config.batchJobLimit = 10
        config.logger = mock.Mock()

        class StubbedIterators(LegacyNewCrashSource):
            def _normal_jobs_iter(self):
                while True:
                    yield None

            def _priority_jobs_iter(self):
                values = [
                    (1, '1234', 1),
                    (2, '2345', 1),
                    (3, '3456', 1),
                    (4, '4567', 1),
                    (5, '5678', 1),
                ]
                for x in values:
                    yield x

        new_crash_source = StubbedIterators(config,
                                       processor_name='victor1234')
        expected = ('1234',
                    '2345',
                    '3456',
                    '4567',
                    '5678',
                   )
        for x, y in zip(new_crash_source, expected):
            self.assertEqual(x, y)

        self.assertEqual(len([x for x in new_crash_source]), 5)

    def test_incoming_job_stream_interleaved(self):
        config = DotDict()
        config.database_class = mock.Mock()
        config.transaction_executor_class = mock.Mock()
        config.batchJobLimit = 10
        config.logger = mock.Mock()

        class StubbedIterators(LegacyNewCrashSource):
            def _normal_jobs_iter(self):
                values = [
                    (1, '1234', 1),
                    (2, '2345', 1),
                    (3, '3456', 1),
                    (4, '4567', 1),
                    (5, '5678', 1),
                    None,
                    None,
                ]
                for x in values:
                    yield x

            def _priority_jobs_iter(self):
                values = [
                    None,
                    (10, 'p1234', 1),
                    (20, 'p2345', 1),
                    None,
                    (30, 'p3456', 1),
                    (40, 'p4567', 1),
                    None,
                    None,
                    (50, 'p5678', 1),
                    None,
                ]
                for x in values:
                    yield x

        new_crash_source = StubbedIterators(config,
                                       processor_name='sherman1234')
        expected = ('1234',
                    'p1234',
                    'p2345',
                    '2345',
                    'p3456',
                    'p4567',
                    '3456',
                    '4567',
                    'p5678',
                    '5678',
                   )
        for x, y in zip(new_crash_source, expected):
            self.assertEqual(x, y)

        self.assertEqual(len([x for x in new_crash_source]), 10)


    def test_priority_jobs_iter_simple(self):
        m_transaction = mock.Mock()
        m_transaction_executor_class = mock.Mock(return_value=m_transaction)
        config = DotDict()
        config.database_class = mock.Mock()
        config.transaction_executor_class = m_transaction_executor_class
        config.batchJobLimit = 10
        config.logger = mock.Mock()

        transaction_returns = (
          'priority_jobs_17',
          [  # fetchall
              (1, '1234', 1, None),
              (2, '2345', 1, None),
              (3, '3456', 1, None),
          ],
          None,  # delete
          None,  # delete
          None,  # delete
          [  # nothing to do
          ],
          [
              (4, '4567', 1, None),
              (5, '5678', 1, None),
          ],
          None,  # delete
          None,  # delete
          [  # nothing to do
          ],
          None,  # drop table
        )
        m_transaction.side_effect = sequencer(*transaction_returns)

        expected_sequence = (
            (1, '1234', 1),
            (2, '2345', 1),
            (3, '3456', 1),
            None,
            (4, '4567', 1),
            (5, '5678', 1),
        )

        new_crash_source = LegacyNewCrashSource(config,
                                       processor_name='dwight')

        for x, y in zip(new_crash_source._priority_jobs_iter(), expected_sequence):
            self.assertEqual(x, y)

        expected_get_priority_jobs_sql = (
          "select"
          "    j.id,"
          "    pj.uuid,"
          "    1,"
          "    j.starteddatetime "
          "from"
          "    jobs j right join priority_jobs_17 pj on j.uuid = pj.uuid"
        )
        expected_delete_one_priority_job_sql = (
          "delete from priority_jobs_17 where uuid = %s"
        )
        expected_transactions = (
            ((new_crash_source._create_priority_jobs,),),
            ((execute_query_fetchall, expected_get_priority_jobs_sql,),),
            ((execute_no_results, expected_delete_one_priority_job_sql,
                ('1234',)),),
            ((execute_no_results, expected_delete_one_priority_job_sql,
                ('2345',)),),
            ((execute_no_results, expected_delete_one_priority_job_sql,
                ('3456',)),),
            ((execute_query_fetchall, expected_get_priority_jobs_sql,),),
            ((execute_query_fetchall, expected_get_priority_jobs_sql,),),
            ((execute_no_results, expected_delete_one_priority_job_sql,
                ('4567',)),),
            ((execute_no_results, expected_delete_one_priority_job_sql,
                ('5678',)),),
            ((execute_query_fetchall, expected_get_priority_jobs_sql,),),
            ((execute_no_results, "drop table priority_jobs_17"),),
        )
        for actual, expected in zip(m_transaction.call_args_list,
                                    expected_transactions):
            self.assertEqual(actual, expected)


    def test_normal_jobs_iter_simple(self):
        m_transaction = mock.Mock()
        m_transaction_executor_class = mock.Mock(return_value=m_transaction)
        config = DotDict()
        config.database_class = mock.Mock()
        config.transaction_executor_class = m_transaction_executor_class
        config.batchJobLimit = 10
        config.logger = mock.Mock()

        transaction_returns = (
          'priority_jobs_17',
          [  # fetchall
              (1, '1234', 1),
              (2, '2345', 1),
              (3, '3456', 1),
          ],
          [  # nothing to do
          ],
          [
              (4, '4567', 1),
              (5, '5678', 1),
          ],
          None,  # drop table
        )
        m_transaction.side_effect = sequencer(*transaction_returns)

        exepected_sequence = (
            (1, '1234', 1),
            (2, '2345', 1),
            (3, '3456', 1),
            None,
            (4, '4567', 1),
            (5, '5678', 1),
        )

        new_crash_source = LegacyNewCrashSource(config,
                                       processor_name='dwight')
        new_crash_source.processor_id = 17
        for x, y in zip(new_crash_source._normal_jobs_iter(), exepected_sequence):
            self.assertEqual(x, y)

        expected_get_normal_sql = (
          "select"
          "    j.id,"
          "    j.uuid,"
          "    priority "
          "from"
          "    jobs j "
          "where"
          "    j.owner = 17"
          "    and j.starteddatetime is null "
          "order by queueddatetime"
          "  limit 10"
        )
        expected_transactions = (
            ((new_crash_source._create_priority_jobs,),),
            ((execute_query_fetchall, expected_get_normal_sql,),),
            ((execute_query_fetchall, expected_get_normal_sql,),),
            ((execute_query_fetchall, expected_get_normal_sql,),),
            ((execute_query_fetchall, expected_get_normal_sql,),),
            ((execute_no_results, "drop table priority_jobs_17"),),
        )
        for actual, expected in zip(m_transaction.call_args_list,
                                    expected_transactions):
            self.assertEqual(actual, expected)

