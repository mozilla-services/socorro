# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from statsd import StatsClient

from configman import RequiredConfig, Namespace, class_converter


#------------------------------------------------------------------------------
def str_to_list(string_list):
    item_list = []
    for x in string_list.split(','):
        item_list.append(x.strip())
    return item_list


#==============================================================================
class StatsdCrashStorage(RequiredConfig):
    """This class is a duck typed crash storage class.  All it does is log
    the calls made to it to statsd.  It can use several different
    implementations of statsd client as specified by the 'statsd_module' and
    'statsd_module_incr_method_name' configuration parameters."""

    required_config = Namespace()
    required_config.add_option(
        'statsd_module',
        doc='the name of module that implements statsd client',
        default='datadog.statsd',
        reference_value_from='resource.statsd',
        from_string_converter=class_converter,
    )
    required_config.add_option(
        'statsd_module_incr_method_name',
        doc='the name of method that implements increment',
        default='increment',
        reference_value_from='resource.statsd',
    )
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
        default='save_processed',
        reference_value_from='resource.statsd',
    )
    required_config.add_option(
        'active_counters_list',
        default='save_processed',
        doc='a comma delimeted list of counters',
        from_string_converter=str_to_list,
        reference_value_from='resource.statsd',
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(StatsdCrashStorage, self).__init__()
        self.config = config
        if config.prefix:
            self.prefix = config.prefix
        else:
            self.prefix = ''
        self.statsd = self.config.statsd_module.statsd(
            config.statsd_host,
            config.statsd_port,
        )
        self.counter_increment = getattr(
            self.statsd,
            config.statsd_module_incr_method_name
        )

    #--------------------------------------------------------------------------
    def _incr(self, name):
        if (
            self.config.statsd_host
            and name in self.config.active_counters_list
        ):
            if self.prefix and name:
                name = '.'.join((self.prefix, name))
            elif self.prefix and not name:
                name =  self.prefix
            elif not name:
                name = 'unknown'
            self.counter_increment(name)

    #--------------------------------------------------------------------------
    def __getattr__(self, attr):
        self._incr(attr)
        return self._dummy_do_nothing_method

    #--------------------------------------------------------------------------
    def _dummy_do_nothing_method(self, *args, **kwargs):
        pass


