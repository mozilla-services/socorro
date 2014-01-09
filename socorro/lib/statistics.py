# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

from statsd import StatsClient

from configman import RequiredConfig, Namespace

def str_to_list(string_list):
    item_list = []
    for x in string_list.split(','):
        item_list.append(x.strip())
    return item_list


class StatisticsForStatsd(RequiredConfig):
    """This class is a wrapper around statsd adding a simple configman
    compatible interface and stats naming scheme.  Code using this class
    will distrubute `incr` calls with names associated with them.  When
    ever an `incr` call is encountered, the name will be paired with the
    name of the statsd names and the increment action fired off.

    This class will only send stats `incr` calls for names that appear in
    the configuration parameter `active_counters_list`.  This enables counters
    to be turned on and off at configuration time."""

    required_config = Namespace()
    required_config.add_option(
        'statsd_host',
        doc='the hostname of statsd',
        default='',
        reference_value_from='resource.statsd',
    )
    required_config.add_option(
        'statsd_port',
        doc='the port number for statsd',
        default=8125,
        reference_value_from='resource.statsd',
    )
    required_config.add_option(
        'prefix',
        doc='a string to be used as the prefix for statsd names',
        default='',
        reference_value_from='resource.statsd',
    )
    required_config.add_option(
        'active_counters_list',
        default='',
        #default='restarts, jobs, criticals, errors, mdsw_failures',
        doc='a comma delimeted list of counters',
        from_string_converter=str_to_list,
        reference_value_from='resource.statsd',
    )

    def __init__(self, config, name):
        super(StatisticsForStatsd, self).__init__()
        self.config = config
        if config.prefix and name:
            self.prefix = '.'.join((config.prefix, name))
        elif config.prefix:
            self.prefix = config.prefix
        elif name:
            self.prefix = name
        else:
            self.prefix = ''
        self.statsd = StatsClient(
            config.statsd_host,
            config.statsd_port,
            self.prefix
        )

    def incr(self, name):
        if (
            self.config.statsd_host
            and name in self.config.active_counters_list
        ):
            if self.prefix and name:
                name = '.'.join((self.prefix, name))
            elif self.prefix:
                name = self.prefix
            elif not name:
                name = 'unknown'
            self.statsd.incr(name)

