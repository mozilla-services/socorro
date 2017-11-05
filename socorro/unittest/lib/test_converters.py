# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import RequiredConfig, Namespace
from configman.converters import to_str
import pytest

from socorro.lib.converters import (
    str_to_classes_in_namespaces_converter,
    change_default,
)
from socorro.unittest.testbase import TestCase


# the following two classes are used in test_classes_in_namespaces_converter1
# and need to be declared at module level scope
class Foo(RequiredConfig):
    required_config = Namespace()
    required_config.add_option('x', default=17)
    required_config.add_option('y', default=23)


class Bar(RequiredConfig):
    required_config = Namespace()
    required_config.add_option('x', default=227)
    required_config.add_option('a', default=11)


# the following two classes are used in test_classes_in_namespaces_converter2
# and test_classes_in_namespaces_converter_3.  They need to be declared at
#module level scope
class Alpha(RequiredConfig):
    required_config = Namespace()
    required_config.add_option('a', doc='a', default=17)

    def __init__(self, config):
        self.config = config
        self.a = config.a

    def to_str(self):
        return "I am an instance of an Alpha object"


class AlphaBad1(Alpha):
    def __init__(self, config):
        super(AlphaBad1, self).__init__(config)
        self.a_type = int

    def to_str(self):
        raise AttributeError


class AlphaBad2(AlphaBad1):
    def to_str(self):
        raise KeyError


class AlphaBad3(AlphaBad1):
    def to_str(self):
        raise TypeError


class Beta(RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        'b',
        doc='b',
        default=23
    )

    def __init__(self, config):
        self.config = config
        self.b = config.b


class TestConverters(TestCase):

    def test_classes_in_namespaces_converter_1(self):
        converter_fn = str_to_classes_in_namespaces_converter()
        class_list_str = (
            'socorro.unittest.lib.test_converters.Foo,'
            'socorro.unittest.lib.test_converters.Bar'
        )
        result = converter_fn(class_list_str)
        assert hasattr(result, 'required_config')
        req = result.required_config
        assert len(req) == 2
        assert 'Foo' in req
        assert len(req.Foo) == 1
        assert 'Bar' in req
        assert len(req.Bar) == 1
        expected = sorted([x.strip() for x in to_str(result).strip("'").split(',')])
        assert sorted([x.strip() for x in class_list_str.split(',')]) == expected

    def test_classes_in_namespaces_converter_2(self):
        converter_fn = str_to_classes_in_namespaces_converter()
        class_sequence = (Foo, Bar)
        # ought to raise TypeError because 'class_sequence' is not a string
        with pytest.raises(TypeError):
            converter_fn(class_sequence)

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

        assert a_new_option_with_a_new_default is not Alpha.required_config.an_option
        assert a_new_option_with_a_new_default.default == '29300'
        assert Alpha.required_config.an_option.default == 19
