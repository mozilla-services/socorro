# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from configman.dotdict import DotDict
from configman import Namespace
from mock import Mock, MagicMock, patch
import pytest

from socorro.lib import transform_rules
from socorro.unittest.testbase import TestCase


def foo(s, d):
    pass


def bar(s, d):
    pass


class RuleTestLaughable(transform_rules.Rule):
    required_config = Namespace()
    required_config.add_option('laughable', default='fred')

    def _predicate(self, *args, **kwargs):
        return self.config.laughable != 'fred'

    def close(self):
        try:
            self.close_counter += 1
        except AttributeError:
            self.close_counter = 1


class RuleTestDangerous(transform_rules.Rule):
    required_config = Namespace()
    required_config.add_option('dangerous', default='sally')

    def _action(self, *args, **kwargs):
        return self.config.dangerous != 'sally'

    def close(self):
        try:
            self.close_counter += 1
        except AttributeError:
            self.close_counter = 1


class RuleTestNoCloseMethod(transform_rules.Rule):

    def _action(self, *args, **kwargs):
        return True


class RuleTestBrokenCloseMethod(transform_rules.Rule):

    def _action(self, *args, **kwargs):
        return true  # noqa

    def close(self):
        # this is deliberately breaking
        raise AttributeError("We're human")


class TestTransformRules(TestCase):

    def test_kw_str_parse(self):
        a = 'a=1, b=2'
        actual = transform_rules.kw_str_parse(a)
        expected = {'a': 1, 'b': 2}
        assert expected == actual

        a = 'a="fred", b=3.1415'
        actual = transform_rules.kw_str_parse(a)
        expected = {'a': 'fred', 'b': 3.1415}
        assert expected == actual

    def test_TransfromRule_init(self):
        r = transform_rules.TransformRule(True, (), {}, True, (), {})
        assert r.predicate is True
        assert r.predicate_args == ()
        assert r.predicate_kwargs == {}
        assert r.action is True
        assert r.action_args == ()
        assert r.action_kwargs == {}

        r = transform_rules.TransformRule(True, '', '', True, '', '')
        assert r.predicate is True
        assert r.predicate_args == ()
        assert r.predicate_kwargs == {}
        assert r.action is True
        assert r.action_args == ()
        assert r.action_kwargs == {}

        r = transform_rules.TransformRule(foo, '', '', bar, '', '')
        assert r.predicate == foo
        assert r.predicate_args == ()
        assert r.predicate_kwargs == {}
        assert r.action == bar
        assert r.action_args == ()
        assert r.action_kwargs == {}

        r = transform_rules.TransformRule(
            'socorro.unittest.lib.test_transform_rules.foo', '', '',
            'socorro.unittest.lib.test_transform_rules.bar', '', '')
        repr_pred = repr(r.predicate)
        assert 'foo' in repr_pred
        assert r.predicate_args == ()
        assert r.predicate_kwargs == {}
        repr_act = repr(r.action)
        assert 'bar' in repr_act
        assert r.action_args == ()
        assert r.action_kwargs == {}

        r = transform_rules.TransformRule(
            'socorro.unittest.lib.test_transform_rules.foo',
            (1,),
            {'a': 13},
            'socorro.unittest.lib.test_transform_rules.bar',
            '',
            ''
        )
        repr_pred = repr(r.predicate)
        assert 'foo' in repr_pred, 'expected "foo" in %s' % repr_pred
        assert r.predicate_args == (1,)
        assert r.predicate_kwargs == {'a': 13}
        repr_act = repr(r.action)
        assert 'bar' in repr_act, 'expected "bar" in %s' % repr_act
        assert r.action_args == ()
        assert r.action_kwargs == {}

        r = transform_rules.TransformRule(
            'socorro.unittest.lib.test_transform_rules.foo',
            '1, 2',
            'a=13',
            'socorro.unittest.lib.test_transform_rules.bar',
            '',
            ''
        )
        repr_pred = repr(r.predicate)
        assert 'foo' in repr_pred, 'expected "foo" in %s' % repr_pred
        assert r.predicate_args == (1, 2)
        assert r.predicate_kwargs == {'a': 13}
        repr_act = repr(r.action)
        assert 'bar' in repr_act, 'expected "bar" in %s' % repr_act
        assert r.action_args == ()
        assert r.action_kwargs == {}

    def test_TransformRule_with_class(self):
        """test to make sure that classes can be used as predicates and
        actions"""
        class MyRule(object):

            def __init__(self, config=None):
                self.predicate_called = False
                self.action_called = False

            def predicate(self):
                self.predicate_called = True
                return True

            def action(self):
                self.action_called = True
                return True
        r = transform_rules.TransformRule(
            MyRule, (), {},
            MyRule, (), {}
        )
        assert r.predicate == r._predicate_implementation.predicate
        assert r.action == r._action_implementation.action
        assert r._action_implementation == r._predicate_implementation
        r.act()
        assert r._predicate_implementation.predicate_called
        assert r._action_implementation.action_called

    def test_TransformRule_with_class_function_mix(self):
        """test to make sure that classes can be mixed with functions as
        predicates and actions"""
        class MyRule(object):

            def __init__(self, config=None):
                self.predicate_called = False
                self.action_called = False

            def predicate(self):
                self.predicate_called = True
                return True

            def action(self):
                self.action_called = True
                return True

        def my_predicate():
            return True

        r = transform_rules.TransformRule(
            my_predicate, (), {},
            MyRule, (), {}
        )
        assert r.predicate == my_predicate
        assert r.action == r._action_implementation.action
        self.assertNotEqual(r._action_implementation,
                            r._predicate_implementation)
        r.act()
        # make sure that the class predicate function was not called
        assert not r._action_implementation.predicate_called
        assert r._action_implementation.action_called

    def test_TransfromRule_function_or_constant(self):
        r = transform_rules.TransformRule.function_invocation_proxy(True, (), {})
        assert r is True
        r = transform_rules.TransformRule.function_invocation_proxy(False, (), {})
        assert r is False

        r = transform_rules.TransformRule.function_invocation_proxy(True, (1, 2, 3), {})
        assert r is True
        r = transform_rules.TransformRule.function_invocation_proxy(False, (), {'a': 13})
        assert r is False

        r = transform_rules.TransformRule.function_invocation_proxy('True', (1, 2, 3), {})
        assert r is True
        r = transform_rules.TransformRule.function_invocation_proxy(None, (), {'a': 13})
        assert r is False

        def fn1(*args, **kwargs):
            return (args, kwargs)

        r = transform_rules.TransformRule.function_invocation_proxy(fn1, (1, 2, 3), {})
        assert r == ((1, 2, 3), {})
        r = transform_rules.TransformRule.function_invocation_proxy(fn1, (1, 2, 3), {'a': 13})
        assert r == ((1, 2, 3), {'a': 13})

    def test_TransfromRule_act(self):
        rule = transform_rules.TransformRule(True, (), {}, True, (), {})
        r = rule.act()
        assert r == (True, True)

        rule = transform_rules.TransformRule(True, (), {}, False, (), {})
        r = rule.act()
        assert r == (True, False)

        def pred1(s, d, fred):
            return bool(fred)
        s = {'dwight': 96}
        d = {}

        rule = transform_rules.TransformRule(pred1, (True), {}, False, (), {})
        r = rule.act(s, d)
        assert r == (True, False)

        rule = transform_rules.TransformRule(pred1, (), {'fred': True},
                                             False, (), {})
        r = rule.act(s, d)
        assert r == (True, False)

        rule = transform_rules.TransformRule(pred1, (), {'fred': False},
                                             False, (), {})
        r = rule.act(s, d)
        assert r == (False, None)

        def copy1(s, d, s_key, d_key):
            d[d_key] = s[s_key]
            return True

        rule = transform_rules.TransformRule(pred1, (), {'fred': True},
                                             copy1, (),
                                             's_key="dwight", d_key="wilma"')
        r = rule.act(s, d)
        assert r == (True, True)
        assert s['dwight'] == 96
        assert d['wilma'] == 96

    def test_TransformRuleSystem_init(self):
        rules = transform_rules.TransformRuleSystem()
        assert rules.rules == []

    def test_TransformRuleSystem_load_rules(self):
        rules = transform_rules.TransformRuleSystem()
        some_rules = [(True, '', '', True, '', ''),
                      (False, '', '', False, '', '')]
        rules.load_rules(some_rules)
        expected = [transform_rules.TransformRule(*(True, (), {},
                                                    True, (), {})),
                    transform_rules.TransformRule(*(False, (), {},
                                                    False, (), {}))]
        assert rules.rules == expected

    def test_TransformRuleSystem_apply_all_rules(self):

        quit_check_mock = Mock()

        def assign_1(s, d):
            d['one'] = 1
            return True

        def increment_1(s, d):
            try:
                d['one'] += 1
                return True
            except KeyError:
                return False

        some_rules = [(True, '', '', increment_1, '', ''),
                      (True, '', '', assign_1, '', ''),
                      (False, '', '', increment_1, '', ''),
                      (True, '', '', increment_1, '', ''),
                      ]
        rules = transform_rules.TransformRuleSystem(quit_check=quit_check_mock)
        rules.load_rules(some_rules)
        s = {}
        d = {}
        rules.apply_all_rules(s, d)
        assert d == {'one': 2}
        assert quit_check_mock.call_count == 4

    def test_rule_simple(self):
        fake_config = DotDict()
        fake_config.logger = Mock()
        fake_config.chatty_rules = False
        fake_config.chatty = False

        r1 = transform_rules.Rule(fake_config)
        assert r1.predicate(None, None, None, None) is True
        assert r1.action(None, None, None, None) is True
        assert r1.act() == (True, True)

        class BadPredicate(transform_rules.Rule):

            def _predicate(self, *args, **kwargs):
                return False

        r2 = BadPredicate(fake_config)
        assert r2.predicate(None, None, None, None) is False
        assert r2.action(None, None, None, None) is True
        assert r2.act() == (False, None)

        class BadAction(transform_rules.Rule):

            def _action(self, *args, **kwargs):
                return False

        r3 = BadAction(fake_config)
        assert r3.predicate(None, None, None, None) is True
        assert r3.action(None, None, None, None) is False
        assert r3.act() == (True, False)

    def test_rule_exceptions(self):
        fake_config = DotDict()
        fake_config.logger = Mock()
        fake_config.chatty_rules = False
        fake_config.chatty = False

        class BadPredicate(transform_rules.Rule):

            def _predicate(self, *args, **kwargs):
                raise Exception("highwater")

        r2 = BadPredicate(fake_config)
        assert not fake_config.logger.debug.called
        fake_config.logger.debug.reset_mock()

        assert r2.predicate(None, None, None, None) is False
        assert fake_config.logger.debug.called
        fake_config.logger.debug.reset_mock()

        assert r2.action(None, None, None, None) is True
        assert not fake_config.logger.debug.called
        fake_config.logger.debug.reset_mock()

        assert r2.act() == (False, None)
        assert fake_config.logger.debug.called
        fake_config.logger.debug.reset_mock()

        class BadAction(transform_rules.Rule):

            def _action(self, *args, **kwargs):
                raise Exception("highwater")

        r3 = BadAction(fake_config)
        assert not fake_config.logger.debug.called
        fake_config.logger.debug.reset_mock()

        assert r3.predicate(None, None, None, None) is True
        assert not fake_config.logger.debug.called
        fake_config.logger.debug.reset_mock()

        assert r3.action(None, None, None, None) is False
        assert fake_config.logger.debug.called
        fake_config.logger.debug.reset_mock()

        assert r3.act() == (True, False)
        assert fake_config.logger.debug.called
        fake_config.logger.debug.reset_mock()

    @patch('socorro.lib.raven_client.raven')
    def test_rule_exceptions_send_to_sentry(self, mock_raven):

        captured_exceptions = []  # a global

        def mock_capture_exception():
            exc_info = sys.exc_info()
            captured_exceptions.append(exc_info[1])
            return 'someidentifier'

        client = MagicMock()

        def mock_Client(**config):
            if config['dsn'] == 'Not a valid DSN but truish':
                raise Exception('Bad DSN!')
            client.config = config
            client.captureException.side_effect = mock_capture_exception
            return client

        mock_raven.Client.side_effect = mock_Client

        fake_config = DotDict()
        fake_config.logger = Mock()
        fake_config.chatty_rules = False
        fake_config.chatty = False
        fake_config.sentry = DotDict()

        class SomeError(Exception):
            pass

        class BadPredicate(transform_rules.Rule):

            def _predicate(self, *args, **kwargs):
                raise SomeError("highwater")

        assert BadPredicate(fake_config).predicate() is False
        fake_config.logger.warning.assert_called_with(
            'Raven DSN is not configured and an exception happened'
        )

        fake_config.sentry.dsn = 'Not a valid DSN but truish'
        assert BadPredicate(fake_config).predicate() is False
        # This happens because the DSN is not valid, so raven
        # immediately rejects it.
        fake_config.logger.error.assert_called_with(
            'Unable to report error with Raven',
            exc_info=True,
        )

        fake_config.sentry.dsn = (
            'https://6e48583:e484@sentry.example.com/01'
        )
        assert BadPredicate(fake_config).predicate() is False
        fake_config.logger.info.assert_called_with(
            'Error captured in Sentry! Reference: someidentifier'
        )
        assert len(captured_exceptions) == 1
        exc = captured_exceptions[0]
        assert isinstance(exc, SomeError)

        class BadAction(transform_rules.Rule):

            def _action(self, *args, **kwargs):
                raise SomeError("highwater")

        assert BadAction(fake_config).action() is False
        assert len(captured_exceptions) == 2
        exc = captured_exceptions[1]
        assert isinstance(exc, SomeError)

    @patch('socorro.lib.raven_client.raven')
    def test_rule_exceptions_send_to_sentry_with_crash_id(self, mock_raven):

        def mock_capture_exception():
            return 'someidentifier'

        client = MagicMock()
        extras = []

        def mock_context_merge(context):
            extras.append(context['extra'])

        def mock_Client(**config):
            client.config = config
            client.context.merge.side_effect = mock_context_merge
            client.captureException.side_effect = mock_capture_exception
            return client

        mock_raven.Client.side_effect = mock_Client

        fake_config = DotDict()
        fake_config.logger = Mock()
        fake_config.chatty_rules = False
        fake_config.chatty = False
        fake_config.sentry = DotDict()
        fake_config.sentry.dsn = (
            'https://6e48583:e484@sentry.example.com/01'
        )

        class BadPredicate(transform_rules.Rule):

            def _predicate(self, *args, **kwargs):
                raise NameError("highwater")

        p = BadPredicate(fake_config)
        raw_crash = {'uuid': 'ABC123'}
        assert p.predicate(raw_crash) is False
        fake_config.logger.info.assert_called_with(
            'Error captured in Sentry! Reference: someidentifier'
        )

        # When the client was created and the extra context
        # merged, we can expect that it included a tag and a crash_id
        assert len(extras) == 1
        assert extras[0]['tag'] == 'predicate'
        assert extras[0]['crash_id'] == 'ABC123'

    def test_rules_in_config(self):
        config = DotDict()
        config.chatty_rules = False
        config.chatty = False
        config.tag = 'test.rule'
        config.action = 'apply_all_rules'
        config['RuleTestLaughable.laughable'] = 'wilma'
        config['RuleTestDangerous.dangerous'] = 'dwight'
        config.rules_list = DotDict()
        config.rules_list.class_list = [
            (
                'RuleTestLaughable',
                RuleTestLaughable,
                'RuleTestLaughable'
            ),
            (
                'RuleTestDangerous',
                RuleTestDangerous,
                'RuleTestDangerous'
            )
        ]
        trs = transform_rules.TransformRuleSystem(config)

        assert isinstance(trs.rules[0], RuleTestLaughable)
        assert isinstance(trs.rules[1], RuleTestDangerous)
        assert trs.rules[0].predicate(None)
        assert trs.rules[1].action(None)

    def test_rules_close(self):
        config = DotDict()
        config.logger = Mock().s
        config.chatty_rules = False
        config.chatty = False
        config.tag = 'test.rule'
        config.action = 'apply_all_rules'
        config['RuleTestLaughable.laughable'] = 'wilma'
        config['RuleTestDangerous.dangerous'] = 'dwight'
        config.rules_list = DotDict()
        config.rules_list.class_list = [
            (
                'RuleTestLaughable',
                RuleTestLaughable,
                'RuleTestLaughable'
            ),
            (
                'RuleTestDangerous',
                RuleTestDangerous,
                'RuleTestDangerous'
            )
        ]
        trs = transform_rules.TransformRuleSystem(config)

        trs.close()

        assert trs.rules[0].close_counter == 1
        assert trs.rules[1].close_counter == 1

    def test_rules_close_if_close_method_available(self):
        config = DotDict()
        config.logger = Mock()
        config.chatty_rules = False
        config.chatty = False
        config.tag = 'test.rule'
        config.action = 'apply_all_rules'
        config.rules_list = DotDict()
        config.rules_list.class_list = [
            (
                'RuleTestNoCloseMethod',
                RuleTestNoCloseMethod,
                'RuleTestNoCloseMethod'
            ),
            (
                'RuleTestDangerous',
                RuleTestDangerous,
                'RuleTestDangerous'
            )
        ]
        trs = transform_rules.TransformRuleSystem(config)
        trs.close()

        assert len(config.logger.debug.mock_calls) == 3
        config.logger.debug.assert_any_call(
            'trying to close %s',
            'socorro.unittest.lib.test_transform_rules.'
            'RuleTestNoCloseMethod'
        )
        config.logger.debug.assert_any_call(
            'trying to close %s',
            'socorro.unittest.lib.test_transform_rules.'
            'RuleTestDangerous'
        )
        config.logger.debug.assert_any_call(
            '%s has no close',
            'socorro.unittest.lib.test_transform_rules.'
            'RuleTestNoCloseMethod'
        )

    def test_rules_close_bubble_close_errors(self):
        config = DotDict()
        config.logger = Mock()
        config.tag = 'test.rule'
        config.action = 'apply_all_rules'
        config.rules_list = DotDict()
        config.rules_list.class_list = [
            (
                'RuleTestBrokenCloseMethod',
                RuleTestBrokenCloseMethod,
                'RuleTestBrokenCloseMethod'
            ),
        ]
        trs = transform_rules.TransformRuleSystem(config)
        with pytest.raises(AttributeError):
            trs.close()

        assert len(config.logger.debug.mock_calls) == 1
        config.logger.debug.assert_any_call(
            'trying to close %s',
            'socorro.unittest.lib.test_transform_rules.'
            'RuleTestBrokenCloseMethod'
        )
