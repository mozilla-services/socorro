# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace, RequiredConfig
from configman.converters import class_converter

from functools import partial

#==============================================================================
class RMQNewCrashSource(RequiredConfig):
    """this class is a refactoring of the iteratior portion of the legacy
    Socorro processor.  It isolates just the part of fetching the ooids of
    jobs to be processed"""
    required_config = Namespace()
    required_config.source.add_option(
        'crashstorage_class',
        doc='the source storage class',
        default='socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, processor_name, quit_check_callback=None):
        self.config = config
        self.crash_store = config.crashstorage_class(config)

    #--------------------------------------------------------------------------
    def close(self):
        pass

    #--------------------------------------------------------------------------
    def __iter__(self):
        """an adapter that allows this class can serve as an iterator in a
        fetch_transform_save app"""
        for a_crash_id in self.crash_store.new_crashes():
            yield (
                (a_crash_id,), 
                {'finished_func': partial(
                    self.crash_store._ack_crash,
                    a_crash_id
                )}
            )

    #--------------------------------------------------------------------------
    def __call__(self):
        return self.__iter__()
