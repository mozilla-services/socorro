import unittest
from mock import Mock

from configman import ConfigurationManager

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp

from socorro.lib.util import DotDict, SilentFakeLogger


class TestFetchTransformSaveApp(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass


    def test_bogus_source_iter_and_worker(self):
        class TestFTSAppClass(FetchTransformSaveApp):
            def __init__(self, config):
                super(TestFTSAppClass, self).__init__(config)
                self.the_list = []

            def _setup_source_and_destination(self):
                pass

            def source_iterator(self):
                for x in xrange(5):
                    yield ((x,), {})

            def transform(self, anItem):
                self.the_list.append(anItem)

        logger = SilentFakeLogger()
        config = DotDict({ 'logger': logger,
                           'number_of_threads': 2,
                           'maximum_queue_size': 2,
                           'source': DotDict({'crashstorage': None}),
                           'destination':DotDict({'crashstorage': None})
                         })

        fts_app = TestFTSAppClass(config)
        fts_app.main()
        self.assertTrue(len(fts_app.the_list) == 5,
                        'expected to do 5 inserts, '
                          'but %d were done instead' % len(fts_app.the_list))
        self.assertTrue(sorted(fts_app.the_list) == range(5),
                        'expected %s, but got %s' % (range(5),
                                                     sorted(fts_app.the_list)))


    def test_bogus_source_and_destination(self):
        class NonInfiniteFTSAppClass(FetchTransformSaveApp):
            def source_iterator(self):
                for x in self.source.new_crashes():
                    yield ((x,), {})

        class FakeStorageSource(object):
            def __init__(self, config, quit_check_callback):
                self.store = DotDict({'1234': DotDict({'ooid': '1234',
                                                       'Product': 'FireFloozy',
                                                       'Version': '1.0'}),
                                      '1235': DotDict({'ooid': '1235',
                                                       'Product': 'ThunderRat',
                                                       'Version': '1.0'}),
                                      '1236': DotDict({'ooid': '1236',
                                                       'Product': 'Caminimal',
                                                       'Version': '1.0'}),
                                      '1237': DotDict({'ooid': '1237',
                                                       'Product': 'Fennicky',
                                                       'Version': '1.0'}),
                                     })
            def get_raw_crash(self, ooid):
                return self.store[ooid]
            def get_dump(self, ooid):
                return 'this is a fake dump'
            def new_ooids(self):
                for k in self.store.keys():
                    yield k


        class FakeStorageDestination(object):
            def __init__(self, config, quit_check_callback):
                self.store = DotDict()
                self.dumps = DotDict()
            def save_raw_crash(self, raw_crash, dump):
                self.store[raw_crash.ooid] = raw_crash
                self.dumps[raw_crash.ooid] = dump

        logger = SilentFakeLogger()
        config = DotDict({ 'logger': logger,
                           'number_of_threads': 2,
                           'maximum_queue_size': 2,
                           'source': DotDict({'crashstorage':
                                                  FakeStorageSource}),
                           'destination':DotDict({'crashstorage':
                                                      FakeStorageDestination})
                         })

        fts_app = NonInfiniteFTSAppClass(config)
        fts_app.main()

        source = fts_app.source
        destination = fts_app.destination

        self.assertEqual(source.store, destination.store)
        self.assertEqual(len(destination.dumps), 4)
        self.assertEqual(destination.dumps['1237'], source.get_dump('1237'))


    def test_source_iterator(self):
        class FakeStorageSource(object):
            def __init__(self):
                self.first = True

            def new_ooids(self):
                if self.first:
                    self.first = False
                else:
                    for k in range(999):
                        yield k
                    for k in range(2):
                        yield None


        class FakeStorageDestination(object):
            def __init__(self, config, quit_check_callback):
                self.store = DotDict()
                self.dumps = DotDict()
            def save_raw_crash(self, raw_crash, dump):
                self.store[raw_crash.ooid] = raw_crash
                self.dumps[raw_crash.ooid] = dump

        logger = SilentFakeLogger()
        config = DotDict({ 'logger': logger,
                           'number_of_threads': 2,
                           'maximum_queue_size': 2,
                           'source': DotDict({'crashstorage':
                                                  FakeStorageSource}),
                           'destination':DotDict({'crashstorage':
                                                      FakeStorageDestination})
                         })

        fts_app = FetchTransformSaveApp(config)
        fts_app.source = FakeStorageSource()
        fts_app.destination = FakeStorageDestination
        error_detected = False
        for x, y in zip(xrange(1002), (a for a in fts_app.source_iterator())):
            if x == 0:
                self.assertTrue(y is None)
            elif x < 1000:
                if x - 1 != y[0][0] and not error_detected:
                    error_detected = True
                    self.assertEqual(x, y,
                                     'iterator fails on iteration %d' % x)
            else:
                print x, y
                if y is not None and not error_detected:
                    error_detected = True
                    self.assertTrue(x is None,
                                    'iterator fails on iteration %d' % x)


    def test_no_source(self):
        class FakeStorageDestination(object):
            def __init__(self, config, quit_check_callback):
                self.store = DotDict()
                self.dumps = DotDict()
            def save_raw_crash(self, raw_crash, dump):
                self.store[raw_crash.ooid] = raw_crash
                self.dumps[raw_crash.ooid] = dump

        logger = SilentFakeLogger()
        config = DotDict({ 'logger': logger,
                           'number_of_threads': 2,
                           'maximum_queue_size': 2,
                           'source': DotDict({'crashstorage':
                                                  None}),
                           'destination':DotDict({'crashstorage':
                                                      FakeStorageDestination})
                         })

        fts_app = FetchTransformSaveApp(config)

        self.assertRaises(TypeError, fts_app.main)



    def test_no_destination(self):
        class FakeStorageSource(object):
            def __init__(self, config, quit_check_callback):
                self.store = DotDict({'1234': DotDict({'ooid': '1234',
                                                       'Product': 'FireFloozy',
                                                       'Version': '1.0'}),
                                      '1235': DotDict({'ooid': '1235',
                                                       'Product': 'ThunderRat',
                                                       'Version': '1.0'}),
                                      '1236': DotDict({'ooid': '1236',
                                                       'Product': 'Caminimal',
                                                       'Version': '1.0'}),
                                      '1237': DotDict({'ooid': '1237',
                                                       'Product': 'Fennicky',
                                                       'Version': '1.0'}),
                                     })
            def get_raw_crash(self, ooid):
                return self.store[ooid]
            def get_dump(self, ooid):
                return 'this is a fake dump'
            def new_ooids(self):
                for k in self.store.keys():
                    yield k

        logger = SilentFakeLogger()
        config = DotDict({ 'logger': logger,
                           'number_of_threads': 2,
                           'maximum_queue_size': 2,
                           'source': DotDict({'crashstorage':
                                                  FakeStorageSource}),
                           'destination':DotDict({'crashstorage':
                                                      None})
                         })

        fts_app = FetchTransformSaveApp(config)

        self.assertRaises(TypeError, fts_app.main)


