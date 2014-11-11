# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_
from unittest import TestCase

from socorro.dataservice.util import (
    string_to_list,
    classes_in_namespaces_converter,
)


#==============================================================================
class TestSupportClassificationRule(TestCase):

    #--------------------------------------------------------------------------
    def test_string_to_list(self):
        s = string_to_list("1,2,3,4")
        eq_(s, ['1', '2', '3', '4'])
        s = string_to_list("1,, 2  ,3 ,    4")
        eq_(s, ['1', '2', '3', '4'])

        # doesn't respect embedded quotes,
        s = string_to_list("'1,, 2 ' ,3 , '   4'")
        eq_(s, ["'1", "2 '", '3', "'   4'"])

    #--------------------------------------------------------------------------
    def test_classes_in_namespaces_converter(self):
        class A(object):
            pass

        class B(object):
            pass

        class C(object):
            pass

        class_list_converter = classes_in_namespaces_converter(
            name_of_class_option='a_class'
        )

        i = class_list_converter('A,B,C')

        eq_(i.subordinate_namespace_names, ['A', 'B', 'C'])
        eq_(i.class_option_name, 'a_class')
        ok_(i.required_config)
        eq_(len(i.required_config), 3)
        class_keys_in_namespaces = [
            x for x in i.required_config.keys_breadth_first()
        ]
        eq_(  # order is preserved
            class_keys_in_namespaces,
            ['A.a_class', 'B.a_class', 'C.a_class']
        )

        classes = [A, B, C]
        class_options_from_namespaces = [
            i.required_config[k] for k in class_keys_in_namespaces
        ]
        for bare_class, class_wrapped_in_option_object in zip(
            classes,
            class_options_from_namespaces
        ):
            eq_(bare_class.__name__, class_wrapped_in_option_object.default)
