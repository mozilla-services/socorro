from nose.tools import eq_, ok_

from configman import ConfigurationManager, RequiredConfig, Namespace
from configman.converters import to_str, str_to_python_object

from socorro.lib.converters import (
    str_to_classes_in_namespaces_converter,
    change_default
)
from socorro.unittest.testbase import TestCase

#==============================================================================
# the following two classes are used in test_classes_in_namespaces_converter1
# and need to be declared at module level scope
class Foo(RequiredConfig):
    required_config = Namespace()
    required_config.add_option('x', default=17)
    required_config.add_option('y', default=23)


#==============================================================================
class Bar(RequiredConfig):
    required_config = Namespace()
    required_config.add_option('x', default=227)
    required_config.add_option('a', default=11)


# the following two classes are used in test_classes_in_namespaces_converter2
# and test_classes_in_namespaces_converter_3.  They need to be declared at
#module level scope
#==============================================================================
class Alpha(RequiredConfig):
    required_config = Namespace()
    required_config.add_option('a', doc='a', default=17)

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.a = config.a

    #--------------------------------------------------------------------------
    def to_str(self):
        return "I am an instance of an Alpha object"


#==============================================================================
class AlphaBad1(Alpha):
    def __init__(self, config):
        super(AlphaBad1, self).__init__(config)
        self.a_type = int

    #--------------------------------------------------------------------------
    def to_str(self):
        raise AttributeError


#==============================================================================
class AlphaBad2(AlphaBad1):
    #--------------------------------------------------------------------------
    def to_str(self):
        raise KeyError


#==============================================================================
class AlphaBad3(AlphaBad1):
    #--------------------------------------------------------------------------
    def to_str(self):
        raise TypeError


#==============================================================================
class Beta(RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        'b',
        doc='b',
        default=23
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.b = config.b


#==============================================================================
class TestConverters(TestCase):

    #--------------------------------------------------------------------------
    def test_classes_in_namespaces_converter_1(self):
        converter_fn = str_to_classes_in_namespaces_converter(
            'class_%(name)s'
        )
        class_list_str = (
            'socorro.unittest.lib.test_converters.Foo,'
            'socorro.unittest.lib.test_converters.Bar'
        )
        result = converter_fn(class_list_str)
        self.assertTrue(hasattr(result, 'required_config'))
        req = result.required_config
        self.assertEqual(len(req), 2)
        self.assertTrue('class_Foo' in req)
        self.assertEqual(len(req.class_Foo), 1)
        self.assertTrue('class_Bar' in req)
        self.assertEqual(len(req.class_Bar), 1)
        self.assertEqual(
            sorted([x.strip() for x in class_list_str.split(',')]),
            sorted([
                x.strip() for x in
                to_str(result).strip("'").split(',')
            ])
        )

    #--------------------------------------------------------------------------
    def test_classes_in_namespaces_converter_2(self):
        converter_fn = str_to_classes_in_namespaces_converter(
            'class_%(name)s'
        )
        class_sequence = (Foo, Bar)
        # ought to raise TypeError because 'class_sequence' is not a string
        self.assertRaises(TypeError, converter_fn, class_sequence)

    #--------------------------------------------------------------------------
    def test_classes_in_namespaces_converter_3(self):
        n = Namespace()
        n.add_option(
            'kls_list',
            default=(
                'socorro.unittest.lib.test_converters.Foo, '
                'socorro.unittest.lib.test_converters.Foo, '
                'socorro.unittest.lib.test_converters.Foo'
            ),
            from_string_converter= str_to_classes_in_namespaces_converter(
                '%(name)s_%(index)02d'
            )
        )

        cm = ConfigurationManager(n, argv_source=[])
        config = cm.get_config()

        self.assertEqual(len(config.kls_list.subordinate_namespace_names), 3)
        self.assertTrue('Foo_00' in config)
        self.assertTrue('Foo_01' in config)
        self.assertTrue('Foo_02' in config)

    #--------------------------------------------------------------------------
    def test_classes_in_namespaces_converter_4(self):
        n = Namespace()
        n.add_option(
            'kls_list',
            default=(
                'socorro.unittest.lib.test_converters.Alpha, '
                'socorro.unittest.lib.test_converters.Alpha, '
                'socorro.unittest.lib.test_converters.Alpha'
            ),
            from_string_converter=str_to_classes_in_namespaces_converter(
                '%(name)s_%(index)02d'
            )
        )

        cm = ConfigurationManager(
            n,
            [{
                'kls_list': (
                    'socorro.unittest.lib.test_converters.Alpha, '
                    'socorro.unittest.lib.test_converters.Beta, '
                    'socorro.unittest.lib.test_converters.Beta, '
                    'socorro.unittest.lib.test_converters.Alpha'
                ),
                'Alpha_00.a': 21,
                'Beta_01.b': 38,
            }]
        )
        config = cm.get_config()


        self.assertEqual(len(config.kls_list.subordinate_namespace_names), 4)
        for x in config.kls_list.subordinate_namespace_names:
            self.assertTrue(x in config)
        self.assertEqual(config.Alpha_00.a, 21)
        self.assertEqual(config.Beta_01.b, 38)

    #--------------------------------------------------------------------------
    def test_classes_in_namespaces_converter_5(self):
        n = Namespace()
        n.add_option(
            'kls_list',
            default=(
                'socorro.unittest.lib.test_converters.Alpha, '
                'socorro.unittest.lib.test_converters.Alpha, '
                'socorro.unittest.lib.test_converters.Alpha'
            ),
            from_string_converter=str_to_classes_in_namespaces_converter(
                '%(name)s_%(index)02d'
            )
        )

        cm = ConfigurationManager(
            n,
            [{
                'kls_list': (
                    'socorro.unittest.lib.test_converters.Alpha, '
                    'socorro.unittest.lib.test_converters.Beta, '
                    'socorro.unittest.lib.test_converters.Beta, '
                    'socorro.unittest.lib.test_converters.Alpha'
                ),
                'Alpha_00.a': 21,
                'Beta_01.b': 38,
            }]
        )
        config = cm.get_config()

        self.assertEqual(len(config.kls_list.subordinate_namespace_names), 4)
        for i, (a_class_name, a_class, ns_name) in \
            enumerate(config.kls_list.class_list):
            self.assertTrue(isinstance(a_class_name, str))
            self.assertEqual(a_class_name, a_class.__name__)
            self.assertEqual(ns_name, "%s_%02d" % (a_class_name, i))

    def test_change_default(self):
        class Alpha(RequiredConfig):
            required_config = Namespace()
            required_config.add_option(
                'an_option',
                default=19,
                doc='this is an an_option',
                from_string_converter=str,
            )
        a_new_option_with_a_new_default = change_default(
            Alpha,
            'an_option',
            '29300'
        )

        ok_(
            a_new_option_with_a_new_default
            is not Alpha.required_config.an_option
        )
        eq_(
            a_new_option_with_a_new_default.default,
            '29300'
        )
        eq_(
            Alpha.required_config.an_option.default,
            19
        )
