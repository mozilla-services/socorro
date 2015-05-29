from mock import patch, call, Mock
from nose.tools import eq_, ok_, assert_raises
from socorro.unittest.testbase import TestCase

from configman.dotdict import DotDict

from socorro.external.statsd.crashstorage import StatsdCrashStorage


class TestStatsdCrashStorage(TestCase):

    def setup_config(self, prefix=None):
        config =  DotDict()
        config.statsd_module =  Mock()
        config.statsd_module_incr_method_name =  'increment'
        config.statsd_host = 'some_statsd_host'
        config.statsd_port =  3333
        config.prefix = prefix if prefix else ''
        config.active_counters_list = 'save_processed'

        return config

    def test_save_processed(self):
        config = self.setup_config()
        number_of_calls =  10

        cs =  StatsdCrashStorage(config)
        for x in range(number_of_calls):
            cs.save_processed(x, {})

        statsd_obj =  config.statsd_module.statsd.return_value
        statsd_incr =  statsd_obj.increment

        statsd_obj.increment.assert_has_calls(
            [call('save_processed') for x in range(number_of_calls)]
        )

    def test_save_processed_with_prefix(self):
        config = self.setup_config()
        config.prefix = 'processor'
        number_of_calls =  10

        cs =  StatsdCrashStorage(config)
        for x in range(number_of_calls):
            cs.save_processed(x, {})

        statsd_obj =  config.statsd_module.statsd.return_value
        statsd_incr =  statsd_obj.increment

        statsd_obj.increment.assert_has_calls(
            [call('processor.save_processed') for x in range(number_of_calls)]
        )

    def test_arbitrary_with_prefix(self):
        config = self.setup_config()
        config.prefix = 'processor'
        number_of_calls =  10

        cs =  StatsdCrashStorage(config)
        for x in range(number_of_calls):
            cs.some_random_method(x, {})

        statsd_obj =  config.statsd_module.statsd.return_value
        statsd_incr =  statsd_obj.increment

        # the method is not in the active list so should be ignored
        statsd_obj.increment.assert_has_calls([])

    def test_save_processed_other_incr_method(self):
        config = self.setup_config()
        config.statsd_module_incr_method_name = 'this_is_silly'
        number_of_calls =  10

        cs =  StatsdCrashStorage(config)
        for x in range(number_of_calls):
            cs.save_processed(x, {})

        statsd_obj =  config.statsd_module.statsd.return_value
        statsd_incr =  statsd_obj.this_is_silly

        statsd_obj.this_is_silly.assert_has_calls(
            [call('save_processed') for x in range(number_of_calls)]
        )

    def test_save_processed_with_prefix_other_incr_method(self):
        config = self.setup_config()
        config.statsd_module_incr_method_name = 'this_is_silly'
        config.prefix = 'processor'
        number_of_calls =  10

        cs =  StatsdCrashStorage(config)
        for x in range(number_of_calls):
            cs.save_processed(x, {})

        statsd_obj =  config.statsd_module.statsd.return_value
        statsd_incr =  statsd_obj.this_is_silly

        statsd_obj.this_is_silly.assert_has_calls(
            [call('processor.save_processed') for x in range(number_of_calls)]
        )

    def test_arbitrary_with_prefix_other_incr_method(self):
        config = self.setup_config()
        config.statsd_module_incr_method_name = 'this_is_silly'
        config.prefix = 'processor'
        number_of_calls =  10

        cs =  StatsdCrashStorage(config)
        for x in range(number_of_calls):
            cs.some_random_method(x, {})

        statsd_obj =  config.statsd_module.statsd.return_value
        statsd_incr =  statsd_obj.this_is_silly

        # the method is not in the active list so should be ignored
        statsd_obj.this_is_silly.assert_has_calls([])







