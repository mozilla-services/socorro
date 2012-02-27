import unittest
import socorro.unittest.testlib.util as testutil

import socorro.lib.transform_rules as tr


def assert_expected(actual, expected):
    assert actual == expected, "expected:\n%s\nbut got:\n%s" % (str(expected),
                                                                str(actual))

def assert_expected_same(actual, expected):
    assert actual == expected, "expected:\n%s\nbut got:\n%s" % (expected,
                                                                actual)

def foo(s, d):
    pass

def bar(s, d):
    pass

#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class TestTransformRules(unittest.TestCase):

    def test_kw_str_parse(self):
        a = 'a=1, b=2'
        actual = tr.kw_str_parse(a)
        expected = {'a':1, 'b':2}
        assert_expected(expected, actual)

        a = 'a="fred", b=3.1415'
        actual = tr.kw_str_parse(a)
        expected = {'a':'fred', 'b':3.1415}
        assert_expected(expected, actual)

    def test_TransfromRule_init(self):
        r = tr.TransformRule(True, (), {}, True, (), {})
        assert_expected(r.predicate, True)
        assert_expected(r.predicate_args, ())
        assert_expected(r.predicate_kwargs, {})
        assert_expected(r.action, True)
        assert_expected(r.action_args, ())
        assert_expected(r.action_kwargs, {})

        r = tr.TransformRule(True, '', '', True, '', '')
        assert_expected(r.predicate, True)
        assert_expected(r.predicate_args, ())
        assert_expected(r.predicate_kwargs, {})
        assert_expected(r.action, True)
        assert_expected(r.action_args, ())
        assert_expected(r.action_kwargs, {})

        r = tr.TransformRule(foo, '', '', bar, '', '')
        assert_expected(r.predicate, foo)
        assert_expected(r.predicate_args, ())
        assert_expected(r.predicate_kwargs, {})
        assert_expected(r.action, bar)
        assert_expected(r.action_args, ())
        assert_expected(r.action_kwargs, {})

        r = tr.TransformRule('test_transform_rules.foo', '', '',
                             'test_transform_rules.bar', '', '')
        repr_pred = repr(r.predicate)
        assert 'foo' in repr_pred, 'expected "foo" in %s' % repr_pred
        assert_expected(r.predicate_args, ())
        assert_expected(r.predicate_kwargs, {})
        repr_act = repr(r.action)
        assert 'bar' in repr_act, 'expected "bar" in %s' % repr_act
        assert_expected(r.action_args, ())
        assert_expected(r.action_kwargs, {})

        r = tr.TransformRule('test_transform_rules.foo', (1,), {'a':13},
                             'test_transform_rules.bar', '', '')
        repr_pred = repr(r.predicate)
        assert 'foo' in repr_pred, 'expected "foo" in %s' % repr_pred
        assert_expected(r.predicate_args, (1,))
        assert_expected(r.predicate_kwargs, {'a':13})
        repr_act = repr(r.action)
        assert 'bar' in repr_act, 'expected "bar" in %s' % repr_act
        assert_expected(r.action_args, ())
        assert_expected(r.action_kwargs, {})

        r = tr.TransformRule('test_transform_rules.foo', '1, 2', 'a=13',
                             'test_transform_rules.bar', '', '')
        repr_pred = repr(r.predicate)
        assert 'foo' in repr_pred, 'expected "foo" in %s' % repr_pred
        assert_expected(r.predicate_args, (1,2))
        assert_expected(r.predicate_kwargs, {'a':13})
        repr_act = repr(r.action)
        assert 'bar' in repr_act, 'expected "bar" in %s' % repr_act
        assert_expected(r.action_args, ())
        assert_expected(r.action_kwargs, {})


    def test_TransfromRule_function_or_constant(self):
        r = tr.TransformRule.function_or_constant(True, (), {})
        assert_expected(r, True)
        r = tr.TransformRule.function_or_constant(False, (), {})
        assert_expected(r, False)

        r = tr.TransformRule.function_or_constant(True, (1, 2, 3), {})
        assert_expected(r, True)
        r = tr.TransformRule.function_or_constant(False, (), {'a':13})
        assert_expected(r, False)

        r = tr.TransformRule.function_or_constant('True', (1, 2, 3), {})
        assert_expected(r, True)
        r = tr.TransformRule.function_or_constant(None, (), {'a':13})
        assert_expected(r, False)

        def fn1(*args, **kwargs):
            return (args, kwargs)

        r = tr.TransformRule.function_or_constant(fn1, (1, 2, 3), {})
        assert_expected(r, ((1, 2, 3), {}))
        r = tr.TransformRule.function_or_constant(fn1, (1, 2, 3), {'a':13})
        assert_expected(r, ((1, 2, 3), {'a':13}))


    def test_TransfromRule_act(self):
        rule = tr.TransformRule(True, (), {}, True, (), {})
        r = rule.act(*(), **{})
        assert_expected(r, (True, True))

        rule = tr.TransformRule(True, (), {}, False, (), {})
        r = rule.act(*(), **{})
        assert_expected(r, (True, False))

        def pred1(s, d, fred):
            return bool(fred)
        s = {'dwight': 96}
        d = {}

        rule = tr.TransformRule(pred1, (True), {}, False, (), {})
        r = rule.act(s, d)
        assert_expected(r, (True, False))

        rule = tr.TransformRule(pred1, (), {'fred':True}, False, (), {})
        r = rule.act(s, d)
        assert_expected(r, (True, False))

        rule = tr.TransformRule(pred1, (), {'fred':False}, False, (), {})
        r = rule.act(s, d)
        assert_expected(r, (False, None))

        def copy1(s, d, s_key, d_key):
            d[d_key] = s[s_key]
            return True

        rule = tr.TransformRule(pred1, (), {'fred':True}, copy1, (),
                                's_key="dwight", d_key="wilma"')
        r = rule.act(s, d)
        assert_expected(r, (True, True))
        assert_expected(s['dwight'], 96)
        assert_expected(d['wilma'], 96)


    def test_TransformRuleSystem_init(self):
        rules = tr.TransformRuleSystem()
        assert_expected(rules.rules, [])

    def test_TransformRuleSystem_load_rules(self):
        rules = tr.TransformRuleSystem()
        some_rules = [(True, '', '', True, '', ''),
                      (False, '', '', False, '', '')]
        rules.load_rules(some_rules)
        expected = [tr.TransformRule(*(True, (), {}, True, (), {})),
                    tr.TransformRule(*(False, (), {}, False, (), {}))]
        assert_expected_same(rules.rules, expected)

    def test_TransformRuleSystem_append_rules(self):
        rules = tr.TransformRuleSystem()
        some_rules = [(True, '', '', True, '', ''),
                      (False, '', '', False, '', '')]
        rules.append_rules(some_rules)
        expected = [tr.TransformRule(*(True, (), {}, True, (), {})),
                    tr.TransformRule(*(False, (), {}, False, (), {}))]
        assert_expected_same(rules.rules, expected)

    def test_TransformRuleSystem_apply_all_rules(self):

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
        rules = tr.TransformRuleSystem()
        rules.load_rules(some_rules)
        s = {}
        d = {}
        rules.apply_all_rules(s, d)
        assert_expected(d, {'one': 2})

    def test_TransformRuleSystem_apply_all_until_action_succeeds(self):

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
        rules = tr.TransformRuleSystem()
        rules.load_rules(some_rules)
        s = {}
        d = {}
        rules.apply_until_action_succeeds(s, d)
        assert_expected(d, {'one': 1})


    def test_TransformRuleSystem_apply_all_until_action_fails(self):

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
        rules = tr.TransformRuleSystem()
        rules.load_rules(some_rules)
        s = {}
        d = {}
        rules.apply_until_action_fails(s, d)
        assert_expected(d, {})


    def test_TransformRuleSystem_apply_all_until_predicate_succeeds(self):

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
        rules = tr.TransformRuleSystem()
        rules.load_rules(some_rules)
        s = {}
        d = {}
        rules.apply_until_predicate_succeeds(s, d)
        assert_expected(d, {})

    def test_TransformRuleSystem_apply_all_until_predicate_fails(self):

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
        rules = tr.TransformRuleSystem()
        rules.load_rules(some_rules)
        s = {}
        d = {}
        rules.apply_until_predicate_fails(s, d)
        assert_expected(d, {'one': 1})






