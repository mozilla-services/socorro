# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    PolyStorageError,
    PolyCrashStorage,
    FallbackCrashStorage,
    PrimaryDeferredStorage,
    PrimaryDeferredProcessedStorage
)
from configman import Namespace, ConfigurationManager
from mock import Mock


class A(CrashStorageBase):
    foo = 'a'
    required_config = Namespace()
    required_config.add_option('x',
                               default=1)
    required_config.add_option('y',
                               default=2
                              )

    def __init__(self, config):
        super(A, self).__init__(config)
        self.raw_crash_count = 0

    def save_raw_crash(self, raw_crash, dump):
        pass

    def save_processed_crash(self, processed_crash):
        pass


class B(A):
    foo = 'b'
    required_config = Namespace()
    required_config.add_option('z',
                               default=2
                              )


def fake_quit_check():
    return False


class TestBase(unittest.TestCase):

    def test_basic_crashstorage(self):

        required_config = Namespace()

        mock_logging = Mock()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
          }]
        )

        with config_manager.context() as config:
            crashstorage = CrashStorageBase(
              config,
              quit_check_callback=fake_quit_check
            )
            crashstorage.save_raw_crash({}, 'payload', 'ooid')
            crashstorage.save_processed({})
            self.assertRaises(NotImplementedError,
                              crashstorage.get_raw_crash, 'ooid')
            self.assertRaises(NotImplementedError,
                              crashstorage.get_raw_dump, 'ooid')
            self.assertRaises(NotImplementedError,
                              crashstorage.get_processed, 'ooid')
            self.assertRaises(NotImplementedError,
                              crashstorage.remove, 'ooid')
            self.assertEquals(crashstorage.new_crashes(), [])
            crashstorage.close()

    def test_polyerror(self):
        p = PolyStorageError('hell')
        try:
            try:
                raise NameError('dwight')
            except NameError:
                p.gather_current_exception()
            try:
                raise KeyError('wilma')
            except KeyError:
                p.gather_current_exception()
            try:
                raise AttributeError('sarita')
            except AttributeError:
                p.gather_current_exception()
            raise p
        except PolyStorageError, x:
            self.assertEqual(len(x), 3)
            self.assertTrue(x.has_exceptions())
            types = [NameError, KeyError, AttributeError]
            [self.assertEqual(a[0], b) for a, b in zip(x, types)]
            self.assertTrue(1 not in x)
            self.assertTrue(str(x[0][1]), 'dwight')

            x[0] = x[1]
            self.assertEqual(x[0], x[1])

    def test_poly_crash_storage(self):
        n = Namespace()
        n.add_option(
          'storage',
          default=PolyCrashStorage,
        )
        n.add_option(
          'logger',
          default=mock.Mock(),
        )
        value = {'storage_classes':
                    'socorro.unittest.external.test_crashstorage_base.A,'
                    'socorro.unittest.external.test_crashstorage_base.A,'
                    'socorro.unittest.external.test_crashstorage_base.B',
                 'storage1.y': 37,
                }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            self.assertEqual(config.storage0.crashstorage_class.foo, 'a')
            self.assertEqual(config.storage1.crashstorage_class.foo, 'a')
            self.assertEqual(config.storage1.y, 37)
            self.assertEqual(config.storage2.crashstorage_class.foo, 'b')

            poly_store = config.storage(config)
            l = len(poly_store.storage_namespaces)
            self.assertEqual(l, 3, 'expected poly_store to have lenth of 3, '
                                  'but %d was found instead' % l)
            self.assertEqual(poly_store.storage_namespaces[0], 'storage0')
            self.assertEqual(poly_store.storage_namespaces[1], 'storage1')
            self.assertEqual(poly_store.storage_namespaces[2], 'storage2')
            l = len(poly_store.stores)
            self.assertEqual(l, 3,
                             'expected poly_store.store to have lenth of 3, '
                                  'but %d was found instead' % l)
            self.assertEqual(poly_store.stores.storage0.foo, 'a')
            self.assertEqual(poly_store.stores.storage1.foo, 'a')
            self.assertEqual(poly_store.stores.storage2.foo, 'b')

            raw_crash = {'ooid': ''}
            dump = '12345'
            processed_crash = {'ooid': '', 'product': 17}
            for v in poly_store.stores.itervalues():
                v.save_raw_crash = Mock()
                v.save_processed = Mock()
                v.close = Mock()

            poly_store.save_raw_crash(raw_crash, dump, '')
            for v in poly_store.stores.itervalues():
                v.save_raw_crash.assert_called_once_with(raw_crash, dump, '')

            poly_store.save_processed(processed_crash)
            for v in poly_store.stores.itervalues():
                v.save_processed.assert_called_once_with(processed_crash)

            poly_store.save_raw_and_processed(
              raw_crash,
              dump,
              processed_crash,
              'n'
            )
            for v in poly_store.stores.itervalues():
                v.save_raw_crash.assert_called_with(raw_crash, dump, 'n')
                v.save_processed.assert_called_with(processed_crash)

            raw_crash = {'ooid': 'oaeu'}
            dump = '5432'
            processed_crash = {'ooid': 'aoeu', 'product': 33}

            poly_store.stores['storage1'].save_raw_crash = Mock()
            poly_store.stores['storage1'].save_raw_crash.side_effect = \
                Exception('this is messed up')
            poly_store.stores['storage2'].save_processed = Mock()
            poly_store.stores['storage2'].save_processed.side_effect = \
                Exception('this is messed up')

            self.assertRaises(PolyStorageError,
                              poly_store.save_raw_crash,
                              raw_crash,
                              dump,
                              '')
            for v in poly_store.stores.itervalues():
                v.save_raw_crash.assert_called_with(raw_crash, dump, '')

            self.assertRaises(PolyStorageError,
                              poly_store.save_processed,
                              processed_crash)
            for v in poly_store.stores.itervalues():
                v.save_processed.assert_called_with(processed_crash)

            poly_store.stores['storage2'].close.side_effect = \
                Exception
            self.assertRaises(PolyStorageError,
                              poly_store.close)
            for v in poly_store.stores.itervalues():
                v.close.assert_called_with()

    def test_fallback_crash_storage(self):
        n = Namespace()
        n.add_option(
          'storage',
          default=FallbackCrashStorage,
        )
        n.add_option(
          'logger',
          default=mock.Mock(),
        )
        value = {'primary.storage_class':
                    'socorro.unittest.external.test_crashstorage_base.A',
                 'fallback.storage_class':
                    'socorro.unittest.external.test_crashstorage_base.B',
                }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            self.assertEqual(config.primary.storage_class.foo, 'a')
            self.assertEqual(config.fallback.storage_class.foo, 'b')

            raw_crash = {'ooid': ''}
            crash_id = '1498dee9-9a45-45cc-8ec8-71bb62121203'
            dump = '12345'
            processed_crash = {'ooid': '', 'product': 17}
            fb_store = config.storage(config)

            # save_raw tests
            fb_store.primary_store.save_raw_crash = Mock()
            fb_store.fallback_store.save_raw_crash = Mock()
            fb_store.save_raw_crash(raw_crash, dump, crash_id)
            fb_store.primary_store.save_raw_crash.assert_called_with(
              raw_crash,
              dump,
              crash_id
            )
            self.assertEqual(fb_store.fallback_store.save_raw_crash.call_count,
                             0)

            fb_store.primary_store.save_raw_crash = Mock()
            fb_store.primary_store.save_raw_crash.side_effect = Exception('!')
            fb_store.save_raw_crash(raw_crash, dump, crash_id)
            fb_store.primary_store.save_raw_crash.assert_called_with(
              raw_crash,
              dump,
              crash_id
            )
            fb_store.fallback_store.save_raw_crash.assert_called_with(
              raw_crash,
              dump,
              crash_id
            )

            fb_store.fallback_store.save_raw_crash = Mock()
            fb_store.fallback_store.save_raw_crash.side_effect = Exception('!')
            self.assertRaises(PolyStorageError,
                              fb_store.save_raw_crash,
                              raw_crash,
                              dump,
                              crash_id
                             )
            fb_store.primary_store.save_raw_crash.assert_called_with(
              raw_crash,
              dump,
              crash_id
            )
            fb_store.fallback_store.save_raw_crash.assert_called_with(
              raw_crash,
              dump,
              crash_id
            )

            # save_processed tests
            fb_store.primary_store.save_processed = Mock()
            fb_store.fallback_store.save_processed = Mock()
            fb_store.save_processed(processed_crash)
            fb_store.primary_store.save_processed.assert_called_with(
              processed_crash
            )
            self.assertEqual(fb_store.fallback_store.save_processed.call_count,
                             0)

            fb_store.primary_store.save_processed = Mock()
            fb_store.primary_store.save_processed.side_effect = Exception('!')
            fb_store.save_processed(processed_crash)
            fb_store.primary_store.save_processed.assert_called_with(
              processed_crash
            )
            fb_store.fallback_store.save_processed.assert_called_with(
              processed_crash
            )

            fb_store.fallback_store.save_processed = Mock()
            fb_store.fallback_store.save_processed.side_effect = Exception('!')
            self.assertRaises(PolyStorageError,
                              fb_store.save_processed,
                              processed_crash
                             )
            fb_store.primary_store.save_processed.assert_called_with(
              processed_crash
            )
            fb_store.fallback_store.save_processed.assert_called_with(
              processed_crash
            )

            # close tests
            fb_store.primary_store.close = Mock()
            fb_store.fallback_store.close = Mock()
            fb_store.close()
            fb_store.primary_store.close.assert_called_with()
            fb_store.fallback_store.close.assert_called_with()

            fb_store.primary_store.close = Mock()
            fb_store.fallback_store.close = Mock()
            fb_store.fallback_store.close.side_effect = NotImplementedError()
            fb_store.close()
            fb_store.primary_store.close.assert_called_with()
            fb_store.fallback_store.close.assert_called_with()

            fb_store.primary_store.close = Mock()
            fb_store.primary_store.close.side_effect = Exception('!')
            fb_store.close()
            fb_store.primary_store.close.assert_called_with()
            fb_store.fallback_store.close.assert_called_with()

            fb_store.fallback_store.close = Mock()
            fb_store.fallback_store.close.side_effect = Exception('!')
            self.assertRaises(PolyStorageError,
                              fb_store.close)
            fb_store.primary_store.close.assert_called_with()
            fb_store.fallback_store.close.assert_called_with()

    def test_deferred_crash_storage(self):
        n = Namespace()
        n.add_option(
          'storage',
          default=PrimaryDeferredStorage,
        )
        n.add_option(
          'logger',
          default=mock.Mock(),
        )
        value = {'primary.storage_class':
                    'socorro.unittest.external.test_crashstorage_base.A',
                 'deferred.storage_class':
                    'socorro.unittest.external.test_crashstorage_base.B',
                  'deferral_criteria': lambda x: x.get('foo') == 'foo'
                }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            self.assertEqual(config.primary.storage_class.foo, 'a')
            self.assertEqual(config.deferred.storage_class.foo, 'b')

            raw_crash = {'ooid': ''}
            crash_id = '1498dee9-9a45-45cc-8ec8-71bb62121203'
            dump = '12345'
            deferred_crash = {'ooid': '', 'foo': 'foo'}
            processed_crash = {'ooid': '', 'product': 17}
            pd_store = config.storage(config)

            # save_raw tests
            pd_store.primary_store.save_raw_crash = Mock()
            pd_store.deferred_store.save_raw_crash = Mock()
            pd_store.save_raw_crash(raw_crash, dump, crash_id)
            pd_store.primary_store.save_raw_crash.assert_called_with(
              raw_crash,
              dump,
              crash_id
            )
            self.assertEqual(pd_store.deferred_store.save_raw_crash.call_count,
                             0)

            pd_store.save_raw_crash(deferred_crash, dump, crash_id)
            pd_store.deferred_store.save_raw_crash.assert_called_with(
              deferred_crash,
              dump,
              crash_id
            )

            # save_processed tests
            pd_store.primary_store.save_processed = Mock()
            pd_store.deferred_store.save_processed = Mock()
            pd_store.save_processed(processed_crash)
            pd_store.primary_store.save_processed.assert_called_with(
              processed_crash
            )
            self.assertEqual(pd_store.deferred_store.save_processed.call_count,
                             0)

            pd_store.save_processed(deferred_crash)
            pd_store.deferred_store.save_processed.assert_called_with(
              deferred_crash
            )

            # close tests
            pd_store.primary_store.close = Mock()
            pd_store.deferred_store.close = Mock()
            pd_store.close()
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()

            pd_store.primary_store.close = Mock()
            pd_store.deferred_store.close = Mock()
            pd_store.deferred_store.close.side_effect = NotImplementedError()
            pd_store.close()
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()

            pd_store.primary_store.close = Mock()
            pd_store.primary_store.close.side_effect = Exception('!')
            pd_store.close()
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()

            pd_store.deferred_store.close = Mock()
            pd_store.deferred_store.close.side_effect = Exception('!')
            self.assertRaises(PolyStorageError,
                              pd_store.close)
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()

    def test_processed_crash_storage(self):
        n = Namespace()
        n.add_option(
          'storage',
          default=PrimaryDeferredProcessedStorage,
        )
        n.add_option(
          'logger',
          default=mock.Mock(),
        )
        value = {'primary.storage_class':
                    'socorro.unittest.external.test_crashstorage_base.A',
                 'deferred.storage_class':
                    'socorro.unittest.external.test_crashstorage_base.B',
                 'processed.storage_class':
                    'socorro.unittest.external.test_crashstorage_base.B',
                  'deferral_criteria': lambda x: x.get('foo') == 'foo'
                }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            self.assertEqual(config.primary.storage_class.foo, 'a')
            self.assertEqual(config.deferred.storage_class.foo, 'b')
            self.assertEqual(config.processed.storage_class.foo, 'b')

            raw_crash = {'ooid': ''}
            crash_id = '1498dee9-9a45-45cc-8ec8-71bb62121203'
            dump = '12345'
            deferred_crash = {'ooid': '', 'foo': 'foo'}
            processed_crash = {'ooid': '', 'product': 17}
            pd_store = config.storage(config)

            # save_raw tests
            pd_store.primary_store.save_raw_crash = Mock()
            pd_store.deferred_store.save_raw_crash = Mock()
            pd_store.processed_store.save_raw_crash = Mock()
            pd_store.save_raw_crash(raw_crash, dump, crash_id)
            pd_store.primary_store.save_raw_crash.assert_called_with(
              raw_crash,
              dump,
              crash_id
            )
            self.assertEqual(pd_store.deferred_store.save_raw_crash.call_count,
                             0)

            pd_store.save_raw_crash(deferred_crash, dump, crash_id)
            pd_store.deferred_store.save_raw_crash.assert_called_with(
              deferred_crash,
              dump,
              crash_id
            )

            # save_processed tests
            pd_store.primary_store.save_processed = Mock()
            pd_store.deferred_store.save_processed = Mock()
            pd_store.processed_store.save_processed = Mock()
            pd_store.save_processed(processed_crash)
            pd_store.processed_store.save_processed.assert_called_with(
              processed_crash
            )
            self.assertEqual(pd_store.primary_store.save_processed.call_count,
                             0)

            pd_store.save_processed(deferred_crash)
            pd_store.processed_store.save_processed.assert_called_with(
              deferred_crash
            )

            # close tests
            pd_store.primary_store.close = Mock()
            pd_store.deferred_store.close = Mock()
            pd_store.close()
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()

            pd_store.primary_store.close = Mock()
            pd_store.deferred_store.close = Mock()
            pd_store.deferred_store.close.side_effect = NotImplementedError()
            pd_store.close()
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()

            pd_store.primary_store.close = Mock()
            pd_store.primary_store.close.side_effect = Exception('!')
            pd_store.close()
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()

            pd_store.deferred_store.close = Mock()
            pd_store.deferred_store.close.side_effect = Exception('!')
            self.assertRaises(PolyStorageError,
                              pd_store.close)
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()
