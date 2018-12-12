# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import RequiredConfig, Namespace

from socorro.lib.converters import change_default


class TestConverters(object):
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
