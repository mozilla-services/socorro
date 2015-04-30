import mock
from nose.tools import eq_, ok_
from configman.dotdict import DotDict

from socorro.unittest.testbase import TestCase
from socorro.models.cleaner import (
    EMAIL,
    URL,
    Cleaner,
    SmartWhitelistMatcher,
)


class TestCleaner(TestCase):

    def _config(self):
        return DotDict({
            'whitelist': None,
            'clean_scrub': None,
            'debug': False
        })

    def test_simplest_case(self):
        config = self._config()
        config.whitelist = {'hits': ('foo', 'bar')}
        data = {
            'hits': [
                {'foo': 1,
                 'bar': 2,
                 'baz': 3},
                {'foo': 4,
                 'bar': 5,
                 'baz': 6},
            ]
        }
        cleaner = Cleaner(config)
        cleaner.start(data)
        expect = {
            'hits': [
                {'foo': 1,
                 'bar': 2},
                {'foo': 4,
                 'bar': 5},
            ]
        }
        eq_(data, expect)

    def test_scrub_copy(self):
        config = self._config()
        config.whitelist = {'hits': ('foo', 'bar')}
        data = {
            'hits': [
                {'foo': 1,
                 'bar': 2,
                 'baz': 3},
                {'foo': 4,
                 'bar': 5,
                 'baz': 6},
            ]
        }
        cleaner = Cleaner(config)
        cleaner.start(data)
        expect = {
            'hits': [
                {'foo': 1,
                 'bar': 2},
                {'foo': 4,
                 'bar': 5},
            ]
        }
        eq_(data, expect)

    @mock.patch('warnings.warn')
    def test_simplest_case_with_warning(self, p_warn):
        config = self._config()
        config.debug = True
        config.whitelist = {'hits': ('foo', 'bar')}
        data = {
            'hits': [
                {'foo': 1,
                 'bar': 2,
                 'baz': 3},
                {'foo': 4,
                 'bar': 5,
                 'baz': 6},
            ]
        }
        cleaner = Cleaner(config)
        cleaner.start(data)
        p_warn.assert_called_with("Skipping 'baz'")

    def test_all_dict_data(self):
        config = self._config()
        config.whitelist = {Cleaner.ANY: ('foo', 'bar')}
        data = {
            'WaterWolf': {
                'foo': 1,
                'bar': 2,
                'baz': 3,
            },
            'NightTrain': {
                'foo': 7,
                'bar': 8,
                'baz': 9,
            },
        }
        cleaner = Cleaner(config)
        cleaner.start(data)
        expect = {
            'WaterWolf': {
                'foo': 1,
                'bar': 2,
            },
            'NightTrain': {
                'foo': 7,
                'bar': 8,
            },
        }
        eq_(data, expect)

    def test_simple_list(self):
        config = self._config()
        config.whitelist = ('foo', 'bar')
        data = [
            {
                'foo': 1,
                'bar': 2,
                'baz': 3,
            },
            {
                'foo': 7,
                'bar': 8,
                'baz': 9,
            },
        ]
        cleaner = Cleaner(config)
        cleaner.start(data)
        expect = [
            {
                'foo': 1,
                'bar': 2,
            },
            {
                'foo': 7,
                'bar': 8,
            },
        ]
        eq_(data, expect)

    def test_plain_dict(self):
        config = self._config()
        config.whitelist = ('foo', 'bar')
        data = {
            'foo': 1,
            'bar': 2,
            'baz': 3,
        }
        cleaner = Cleaner(config)
        cleaner.start(data)
        expect = {
            'foo': 1,
            'bar': 2,
        }
        eq_(data, expect)

    def test_dict_data_with_lists(self):
        config = self._config()
        config.whitelist = {
            'hits': {
                Cleaner.ANY: ('foo', 'bar')
            }
        }
        data = {
            'hits': {
                'WaterWolf': [
                    {'foo': 1, 'bar': 2, 'baz': 3},
                    {'foo': 4, 'bar': 5, 'baz': 6}
                ],
                'NightTrain': [
                    {'foo': 7, 'bar': 8, 'baz': 9},
                    {'foo': 10, 'bar': 11, 'baz': 12}
                ]
            }
        }
        cleaner = Cleaner(config)
        cleaner.start(data)
        expect = {
            'hits': {
                'WaterWolf': [
                    {'foo': 1, 'bar': 2},
                    {'foo': 4, 'bar': 5}
                ],
                'NightTrain': [
                    {'foo': 7, 'bar': 8},
                    {'foo': 10, 'bar': 11}
                ]
            }
        }
        eq_(data, expect)

    def test_all_dict_data_deeper(self):
        config = self._config()
        config.whitelist = {Cleaner.ANY: {Cleaner.ANY: ('foo', 'bar')}}
        data = {
            'WaterWolf': {
                '2012': {
                    'foo': 1,
                    'bar': 2,
                    'baz': 3,
                },
                '2013': {
                    'foo': 4,
                    'bar': 5,
                    'baz': 6,
                }
            },
            'NightTrain': {
                '2012': {
                    'foo': 7,
                    'bar': 8,
                    'baz': 9,
                },
                '2013': {
                    'foo': 10,
                    'bar': 11,
                    'baz': 12,
                }
            },
        }
        cleaner = Cleaner(config)
        cleaner.start(data)
        expect = {
            'WaterWolf': {
                '2012': {
                    'foo': 1,
                    'bar': 2,
                },
                '2013': {
                    'foo': 4,
                    'bar': 5,
                }
            },
            'NightTrain': {
                '2012': {
                    'foo': 7,
                    'bar': 8,
                },
                '2013': {
                    'foo': 10,
                    'bar': 11,
                }
            },
        }
        eq_(data, expect)

    def test_with_scrubber_cleaning(self):
        config = self._config()
        config.whitelist = {'hits': ('foo', 'bar', 'baz')}
        data = {
            'hits': [
                {'foo': "Bla bla",
                 'bar': "contact me on big@penis.com",
                 'baz': "when I visited http://www.p0rn.com"},
                {'foo': "Ble ble unconfiged@email.com",
                 'bar': "other things on https://google.com here",
                 'baz': "talk to bill@gates.com"},
            ]
        }
        config.clean_scrub = (
            ('bar', EMAIL),
            ('bar', URL),
            ('baz', URL),
        )
        cleaner = Cleaner(config)
        cleaner.start(data)
        expect = {
            'hits': [
                {'foo': "Bla bla",
                 'bar': "contact me on ",
                 'baz': "when I visited "},
                {'foo': "Ble ble unconfiged@email.com",
                 'bar': "other things on  here",
                 # because 'baz' doesn't have an EMAIL scrubber
                 'baz': "talk to bill@gates.com"},
            ]
        }
        eq_(data, expect)


class TestSmartWhitelistMatcher(TestCase):

    def test_basic_in(self):
        whitelist = ['some', 'thing*']
        matcher = SmartWhitelistMatcher(whitelist)
        ok_('some' in matcher)
        ok_('something' not in matcher)
        ok_('awesome' not in matcher)
        ok_('thing' in matcher)
        ok_('things' in matcher)
        ok_('nothing' not in matcher)
