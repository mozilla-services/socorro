# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy

from configman import Namespace, ConfigurationManager
from configman.dotdict import DotDict
import mock
from mock import Mock
import pytest

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    PolyStorageError,
    PolyCrashStorage,
    FallbackCrashStorage,
    MigrationCrashStorage,
    PrimaryDeferredStorage,
    PrimaryDeferredProcessedStorage,
    Redactor,
    BenchmarkingCrashStorage,
    MemoryDumpsMapping,
    FileDumpsMapping,
    socorrodotdict_to_dict
)
from socorro.lib.util import DotDict as SocorroDotDict
from socorro.unittest.testbase import TestCase


class A(CrashStorageBase):
    foo = 'a'
    required_config = Namespace()
    required_config.add_option('x', default=1)
    required_config.add_option('y', default=2)

    def __init__(self, config, quit_check=None):
        super(A, self).__init__(config, quit_check)
        self.raw_crash_count = 0

    def save_raw_crash(self, raw_crash, dump):
        pass

    def save_processed_crash(self, processed_crash):
        pass


class B(A):
    foo = 'b'
    required_config = Namespace()
    required_config.add_option('z', default=2)


class NonMutatingProcessedCrashCrashStorage(CrashStorageBase):
    def save_raw_and_processed(
        self,
        raw_crash,
        dump,
        processed_crash,
        crash_id
    ):
        # This is sort of a lie, but we lie so that we can verify the code went
        # through the right path.
        del processed_crash['foo']


class MutatingProcessedCrashCrashStorage(CrashStorageBase):
    def is_mutator(self):
        return True

    def save_raw_and_processed(
        self,
        raw_crash,
        dump,
        processed_crash,
        crash_id
    ):
        del processed_crash['foo']


def fake_quit_check():
    return False


class Testsocorrodotdict_to_dict(TestCase):
    def test_primitives(self):
        # Test all the primitives
        assert socorrodotdict_to_dict(None) is None
        assert socorrodotdict_to_dict([]) == []
        assert socorrodotdict_to_dict('') == ''
        assert socorrodotdict_to_dict(1) == 1
        assert socorrodotdict_to_dict({}) == {}

    def test_complex(self):
        def comp(data, expected):
            # First socorrodotdict_to_dict the data and compare it.
            new_dict = socorrodotdict_to_dict(data)
            assert new_dict == expected

            # Now deepcopy the new dict to make sure it's ok.
            copy.deepcopy(new_dict)

        # dict -> dict
        comp({'a': 1}, {'a': 1})

        # outer socorrodotdict -> dict
        comp(SocorroDotDict({'a': 1}), {'a': 1})

        # nested socorrodotdict -> dict
        comp(
            SocorroDotDict({
                'a': 1,
                'b': SocorroDotDict({
                    'a': 2
                })
            }),
            {'a': 1, 'b': {'a': 2}}
        )
        # inner socorrodotdict
        comp(
            {
                'a': 1,
                'b': SocorroDotDict({
                    'a': 2
                })
            },
            {'a': 1, 'b': {'a': 2}}
        )
        # in a list
        comp(
            {
                'a': 1,
                'b': [
                    SocorroDotDict({
                        'a': 2
                    }),
                    3,
                    4
                ]
            },
            {'a': 1, 'b': [{'a': 2}, 3, 4]}
        )
        # mixed dotdicts
        comp(
            DotDict({
                'a': 1,
                'b': SocorroDotDict({
                    'a': 2
                })
            }),
            {'a': 1, 'b': {'a': 2}}
        )


class TestBase(TestCase):

    def test_basic_crashstorage(self):

        required_config = Namespace()

        mock_logging = Mock()
        required_config.add_option('logger', default=mock_logging)
        required_config.update(CrashStorageBase.required_config)

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{
                'logger': mock_logging,
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = CrashStorageBase(
                config,
                quit_check_callback=fake_quit_check
            )
            crashstorage.save_raw_crash({}, 'payload', 'ooid')
            crashstorage.save_processed({})
            with pytest.raises(NotImplementedError):
                crashstorage.get_raw_crash('ooid')

            with pytest.raises(NotImplementedError):
                crashstorage.get_raw_dump('ooid')

            with pytest.raises(NotImplementedError):
                crashstorage.get_unredacted_processed('ooid')

            with pytest.raises(NotImplementedError):
                crashstorage.remove('ooid')

            assert crashstorage.new_crashes() == []
            crashstorage.close()

        with config_manager.context() as config:
            class MyCrashStorageTest(CrashStorageBase):
                def save_raw_crash(self, raw_crash, dumps, crash_id):
                    assert crash_id == "fake_id"
                    assert raw_crash == "fake raw crash"
                    assert sorted(dumps.keys()) == sorted(['one', 'two', 'three'])
                    assert sorted(dumps.values()) == sorted(['eins', 'zwei', 'drei'])

            values = ['eins', 'zwei', 'drei']

            def open_function(*args, **kwargs):
                return values.pop(0)

            crashstorage = MyCrashStorageTest(
                config,
                quit_check_callback=fake_quit_check
            )

            with mock.patch("__builtin__.open") as open_mock:
                open_mock.return_value = mock.MagicMock()
                (
                    open_mock.return_value.__enter__
                    .return_value.read.side_effect
                ) = open_function
                crashstorage.save_raw_crash_with_file_dumps(
                    "fake raw crash",
                    FileDumpsMapping({
                        'one': 'eins',
                        'two': 'zwei',
                        'three': 'drei'
                    }),
                    'fake_id'
                )

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
        except PolyStorageError as x:
            assert len(x) == 3
            assert x.has_exceptions()
            expected = [NameError, KeyError, AttributeError]
            assert [exc[0] for exc in x] == expected
            assert 1 not in x
            assert str(x[0][1]) == 'dwight'
            assert all(
                sample in str(x)
                for sample in ['hell', 'NameError', 'KeyError', 'AttributeError']
            )
            assert (
                str(x) == "hell,NameError('dwight',),KeyError('wilma',),AttributeError('sarita',)"
            )

            x[0] = x[1]
            assert x[0] == x[1]

    def test_polyerror_str_missing_args(self):
        p = PolyStorageError()
        try:
            try:
                raise NameError('dwight')
            except NameError:
                p.gather_current_exception()
            try:
                raise KeyError('wilma')
            except KeyError:
                p.gather_current_exception()
            raise p
        except PolyStorageError as x:
            assert str(x) == "NameError('dwight',),KeyError('wilma',)"

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
        value = {
            'storage_namespaces': 'A,A2,B',
            'A.crashstorage_class': 'socorro.unittest.external.test_crashstorage_base.A',
            'A2.crashstorage_class': 'socorro.unittest.external.test_crashstorage_base.A',
            'B.crashstorage_class': 'socorro.unittest.external.test_crashstorage_base.B',
            'A2.y': 37
        }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            assert config.A.crashstorage_class.foo == 'a'
            assert config.A2.crashstorage_class.foo == 'a'
            assert config.A2.y == 37
            assert config.B.crashstorage_class.foo == 'b'

            poly_store = config.storage(config)
            assert len(poly_store.storage_namespaces) == 3
            assert poly_store.storage_namespaces[0] == 'A'
            assert poly_store.storage_namespaces[1] == 'A2'
            assert poly_store.storage_namespaces[2] == 'B'

            assert len(poly_store.stores) == 3
            assert poly_store.stores.A.foo == 'a'
            assert poly_store.stores.A2.foo == 'a'
            assert poly_store.stores.B.foo == 'b'

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

            expected = Exception('this is messed up')
            poly_store.stores['A2'].save_raw_crash = Mock()
            poly_store.stores['A2'].save_raw_crash.side_effect = expected
            poly_store.stores['B'].save_processed = Mock()
            poly_store.stores['B'].save_processed.side_effect = expected

            with pytest.raises(PolyStorageError):
                poly_store.save_raw_crash(raw_crash, dump, '')

            for v in poly_store.stores.itervalues():
                v.save_raw_crash.assert_called_with(raw_crash, dump, '')

            with pytest.raises(PolyStorageError):
                poly_store.save_processed(processed_crash)

            for v in poly_store.stores.itervalues():
                v.save_processed.assert_called_with(processed_crash)

            with pytest.raises(PolyStorageError):
                poly_store.save_raw_and_processed(raw_crash, dump, processed_crash, 'n')

            for v in poly_store.stores.itervalues():
                v.save_raw_crash.assert_called_with(raw_crash, dump, 'n')
                v.save_processed.assert_called_with(processed_crash)

            poly_store.stores['B'].close.side_effect = Exception
            with pytest.raises(PolyStorageError):
                poly_store.close()

            for v in poly_store.stores.itervalues():
                v.close.assert_called_with()

    def test_poly_crash_storage_processed_crash_immutability(self):
        n = Namespace()
        n.add_option(
            'storage',
            default=PolyCrashStorage,
        )
        n.add_option(
            'logger',
            default=mock.Mock(),
        )
        value = {
            'storage_namespaces': 'store1',
            'store1.crashstorage_class': (
                'socorro.unittest.external.test_crashstorage_base'
                '.MutatingProcessedCrashCrashStorage'
            ),
        }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            raw_crash = {'ooid': '12345'}
            dump = '12345'
            processed_crash = {'foo': 'bar'}

            poly_store = config.storage(config)

            poly_store.save_raw_and_processed(
                raw_crash,
                dump,
                processed_crash,
                'n'
            )
            # It's important to be aware that the only thing
            # MutatingProcessedCrashCrashStorage class does, in its
            # save_raw_and_processed() is that it deletes a key called
            # 'foo'.
            # This test makes sure that the dict processed_crash here
            # is NOT affected.
            assert processed_crash['foo'] == 'bar'

    def test_polycrashstorage_processed_immutability_with_nonmutating(self):
        """Verifies if a crash storage says it doesn't mutate the class that "
        we don't do a deepcopy

        """
        n = Namespace()
        n.add_option(
            'storage',
            default=PolyCrashStorage,
        )
        n.add_option(
            'logger',
            default=mock.Mock(),
        )
        value = {
            'storage_namespaces': 'store1',
            'store1.crashstorage_class': (
                'socorro.unittest.external.test_crashstorage_base'
                '.NonMutatingProcessedCrashCrashStorage'
            ),
        }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            raw_crash = {'ooid': '12345'}
            dump = '12345'
            processed_crash = {'foo': 'bar'}

            poly_store = config.storage(config)

            poly_store.save_raw_and_processed(
                raw_crash,
                dump,
                processed_crash,
                'n'
            )
            # We have a crashstorage that says it's not mutating, but deletes a
            # key so that we can verify that the code went down the right path
            # in the processor.
            assert 'foo' not in processed_crash

    def test_poly_crash_storage_immutability_deeper(self):
        n = Namespace()
        n.add_option(
            'storage',
            default=PolyCrashStorage,
        )
        n.add_option(
            'logger',
            default=mock.Mock(),
        )
        value = {
            'storage_namespaces': 'store1',
            'store1.crashstorage_class': (
                'socorro.unittest.external.test_crashstorage_base'
                '.MutatingProcessedCrashCrashStorage'
            ),
        }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            raw_crash = {'ooid': '12345'}
            dump = '12345'
            processed_crash = {
                'foo': DotDict({'other': 'thing'}),
                'bar': SocorroDotDict({'something': 'else'}),
            }

            poly_store = config.storage(config)

            poly_store.save_raw_and_processed(
                raw_crash,
                dump,
                processed_crash,
                'n'
            )
            assert processed_crash['foo']['other'] == 'thing'
            assert processed_crash['bar']['something'] == 'else'

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
        value = {
            'primary.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.A'
            ),
            'fallback.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.B'
            ),
        }
        cm = ConfigurationManager(
            n,
            values_source_list=[value],
            argv_source=[]
        )
        with cm.context() as config:
            assert config.primary.storage_class.foo == 'a'
            assert config.fallback.storage_class.foo == 'b'

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
            assert fb_store.fallback_store.save_raw_crash.call_count == 0

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
            with pytest.raises(PolyStorageError):
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

            # save_processed tests
            fb_store.primary_store.save_processed = Mock()
            fb_store.fallback_store.save_processed = Mock()
            fb_store.save_processed(processed_crash)
            fb_store.primary_store.save_processed.assert_called_with(
                processed_crash
            )
            assert fb_store.fallback_store.save_processed.call_count == 0

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
            with pytest.raises(PolyStorageError):
                fb_store.save_processed(processed_crash)

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

            with pytest.raises(PolyStorageError):
                fb_store.close()
            fb_store.primary_store.close.assert_called_with()
            fb_store.fallback_store.close.assert_called_with()

    def test_migration_crash_storage(self):
        n = Namespace()
        n.add_option(
            'storage',
            default=MigrationCrashStorage,
        )
        n.add_option(
            'logger',
            default=mock.Mock(),
        )
        value = {
            'primary.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.A'
            ),
            'fallback.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.B'
            ),
            'date_threshold': '150315'
        }
        cm = ConfigurationManager(
            n,
            values_source_list=[value],
            argv_source=[]
        )
        with cm.context() as config:
            raw_crash = {'ooid': ''}
            before_crash_id = '1498dee9-9a45-45cc-8ec8-71bb62150314'
            after_crash_id = '1498dee9-9a45-45cc-8ec8-71bb62150315'
            dump = '12345'
            processed_crash = {'ooid': '', 'product': 17}
            migration_store = config.storage(config)

            # save_raw tests
            # save to primary
            migration_store.primary_store.save_raw_crash = Mock()
            migration_store.fallback_store.save_raw_crash = Mock()
            migration_store.save_raw_crash(raw_crash, dump, after_crash_id)
            migration_store.primary_store.save_raw_crash.assert_called_with(
                raw_crash,
                dump,
                after_crash_id
            )
            assert migration_store.fallback_store.save_raw_crash.call_count == 0

            # save to fallback
            migration_store.primary_store.save_raw_crash = Mock()
            migration_store.fallback_store.save_raw_crash = Mock()
            migration_store.save_raw_crash(raw_crash, dump, before_crash_id)
            assert migration_store.primary_store.save_raw_crash.call_count == 0
            migration_store.fallback_store.save_raw_crash.assert_called_with(
                raw_crash,
                dump,
                before_crash_id
            )

            # save_processed tests
            # save to primary
            processed_crash['crash_id'] = after_crash_id
            migration_store.primary_store.save_processed = Mock()
            migration_store.fallback_store.save_processed = Mock()
            migration_store.save_processed(processed_crash)
            migration_store.primary_store.save_processed.assert_called_with(
                processed_crash
            )
            assert migration_store.fallback_store.save_processed.call_count == 0

            # save to fallback
            processed_crash['crash_id'] = before_crash_id
            migration_store.primary_store.save_processed = Mock()
            migration_store.fallback_store.save_processed = Mock()
            migration_store.save_processed(processed_crash)
            assert migration_store.primary_store.save_processed.call_count == 0
            migration_store.fallback_store.save_processed.assert_called_with(
                processed_crash
            )

            # close tests
            migration_store.primary_store.close = Mock()
            migration_store.fallback_store.close = Mock()
            migration_store.close()
            migration_store.primary_store.close.assert_called_with()
            migration_store.fallback_store.close.assert_called_with()

            migration_store.primary_store.close = Mock()
            migration_store.fallback_store.close = Mock()
            migration_store.fallback_store.close.side_effect = (
                NotImplementedError()
            )
            migration_store.close()
            migration_store.primary_store.close.assert_called_with()
            migration_store.fallback_store.close.assert_called_with()

            migration_store.primary_store.close = Mock()
            migration_store.primary_store.close.side_effect = Exception('!')
            migration_store.close()
            migration_store.primary_store.close.assert_called_with()
            migration_store.fallback_store.close.assert_called_with()

            migration_store.fallback_store.close = Mock()
            migration_store.fallback_store.close.side_effect = Exception('!')

            with pytest.raises(PolyStorageError):
                migration_store.close()
            migration_store.primary_store.close.assert_called_with()
            migration_store.fallback_store.close.assert_called_with()

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
        value = {
            'primary.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.A'
            ),
            'deferred.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.B'
            ),
            'deferral_criteria': lambda x: x.get('foo') == 'foo'
        }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            assert config.primary.storage_class.foo == 'a'
            assert config.deferred.storage_class.foo == 'b'

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
            assert pd_store.deferred_store.save_raw_crash.call_count == 0

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
            assert pd_store.deferred_store.save_processed.call_count == 0

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
            with pytest.raises(PolyStorageError):
                pd_store.close()
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
        value = {
            'primary.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.A'
            ),
            'deferred.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.B'
            ),
            'processed.storage_class': (
                'socorro.unittest.external.test_crashstorage_base.B'
            ),
            'deferral_criteria': lambda x: x.get('foo') == 'foo'
        }
        cm = ConfigurationManager(
            n,
            values_source_list=[value],
            argv_source=[]
        )
        with cm.context() as config:
            assert config.primary.storage_class.foo == 'a'
            assert config.deferred.storage_class.foo == 'b'
            assert config.processed.storage_class.foo == 'b'

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
            assert pd_store.deferred_store.save_raw_crash.call_count == 0

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
            assert pd_store.primary_store.save_processed.call_count == 0

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
            with pytest.raises(PolyStorageError):
                pd_store.close()
            pd_store.primary_store.close.assert_called_with()
            pd_store.deferred_store.close.assert_called_with()


class TestRedactor(TestCase):

    def test_redact(self):

        d = DotDict()
        # these keys survive redaction
        d['a.b.c'] = 11
        d['sensitive.x'] = 2
        d['not_url'] = 'not a url'

        # these keys do not survive redaction
        d['url'] = 'http://very.embarassing.com'
        d['email'] = 'lars@fake.com',
        d['user_id'] = '3333'
        d['exploitability'] = 'yep'
        d['json_dump.sensitive'] = 22
        d['upload_file_minidump_flash1.json_dump.sensitive'] = 33
        d['upload_file_minidump_flash2.json_dump.sensitive'] = 44
        d['upload_file_minidump_browser.json_dump.sensitive.exploitable'] = 55
        d['upload_file_minidump_browser.json_dump.sensitive.secret'] = 66
        d['memory_info'] = {'incriminating_memory': 'call the FBI'}

        assert 'json_dump' in d

        config = DotDict()
        config.forbidden_keys = Redactor.required_config.forbidden_keys.default

        expected_surviving_keys = [
            'a',
            'sensitive',
            'not_url',
            'json_dump',
            'upload_file_minidump_flash1',
            'upload_file_minidump_flash2',
            'upload_file_minidump_browser'
        ]
        expected_surviving_keys.sort()

        redactor = Redactor(config)
        redactor(d)
        actual_surviving_keys = [x for x in d.keys()]
        actual_surviving_keys.sort()
        assert actual_surviving_keys == expected_surviving_keys


class TestBench(TestCase):

    def test_benchmarking_crashstore(self):
        required_config = Namespace()

        mock_logging = Mock()
        required_config.add_option('logger', default=mock_logging)
        required_config.update(BenchmarkingCrashStorage.get_required_config())
        fake_crash_store = Mock()

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{
                'logger': mock_logging,
                'wrapped_crashstore': fake_crash_store,
                'benchmark_tag': 'test'
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = BenchmarkingCrashStorage(
                config,
                quit_check_callback=fake_quit_check
            )
            crashstorage.start_timer = lambda: 0
            crashstorage.end_timer = lambda: 1
            fake_crash_store.assert_called_with(config, fake_quit_check)

            crashstorage.save_raw_crash({}, 'payload', 'ooid')
            crashstorage.wrapped_crashstore.save_raw_crash.assert_called_with(
                {},
                'payload',
                'ooid'
            )
            mock_logging.debug.assert_called_with(
                '%s save_raw_crash %s',
                'test',
                1
            )
            mock_logging.debug.reset_mock()

            crashstorage.save_processed({})
            crashstorage.wrapped_crashstore.save_processed.assert_called_with(
                {}
            )
            mock_logging.debug.assert_called_with(
                '%s save_processed %s',
                'test',
                1
            )
            mock_logging.debug.reset_mock()

            crashstorage.save_raw_and_processed({}, 'payload', {}, 'ooid')
            crashstorage.wrapped_crashstore.save_raw_and_processed \
                .assert_called_with(
                    {},
                    'payload',
                    {},
                    'ooid'
                )
            mock_logging.debug.assert_called_with(
                '%s save_raw_and_processed %s',
                'test',
                1
            )
            mock_logging.debug.reset_mock()

            crashstorage.get_raw_crash('uuid')
            crashstorage.wrapped_crashstore.get_raw_crash.assert_called_with(
                'uuid'
            )
            mock_logging.debug.assert_called_with(
                '%s get_raw_crash %s',
                'test',
                1
            )
            mock_logging.debug.reset_mock()

            crashstorage.get_raw_dump('uuid')
            crashstorage.wrapped_crashstore.get_raw_dump.assert_called_with(
                'uuid'
            )
            mock_logging.debug.assert_called_with(
                '%s get_raw_dump %s',
                'test',
                1
            )
            mock_logging.debug.reset_mock()

            crashstorage.get_raw_dumps('uuid')
            crashstorage.wrapped_crashstore.get_raw_dumps.assert_called_with(
                'uuid'
            )
            mock_logging.debug.assert_called_with(
                '%s get_raw_dumps %s',
                'test',
                1
            )
            mock_logging.debug.reset_mock()

            crashstorage.get_raw_dumps_as_files('uuid')
            crashstorage.wrapped_crashstore.get_raw_dumps_as_files \
                .assert_called_with(
                    'uuid'
                )
            mock_logging.debug.assert_called_with(
                '%s get_raw_dumps_as_files %s',
                'test',
                1
            )
            mock_logging.debug.reset_mock()

            crashstorage.get_unredacted_processed('uuid')
            crashstorage.wrapped_crashstore.get_unredacted_processed \
                .assert_called_with(
                    'uuid'
                )
            mock_logging.debug.assert_called_with(
                '%s get_unredacted_processed %s',
                'test',
                1
            )
            mock_logging.debug.reset_mock()


class TestDumpsMappings(TestCase):

    def test_simple(self):
        mdm = MemoryDumpsMapping({
            'upload_file_minidump': 'binary_data',
            'moar_dump': "more binary data",
        })
        assert mdm.as_memory_dumps_mapping() is mdm
        fdm = mdm.as_file_dumps_mapping(
            'a',
            '/tmp',
            'dump'
        )
        assert fdm.as_file_dumps_mapping() is fdm
        assert fdm.as_memory_dumps_mapping() == mdm
