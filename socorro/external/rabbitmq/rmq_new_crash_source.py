# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace, RequiredConfig
from configman.converters import class_converter

from functools import partial


#==============================================================================
class RMQNewCrashSource(RequiredConfig):
    """An iterable of crashes from RabbitMQ"""

    required_config = Namespace()
    required_config.add_option(
        'crashstorage_class',
        doc='the source storage class',
        default='socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, processor_name, quit_check_callback=None):
        self.crash_store = config.crashstorage_class(config)

    #--------------------------------------------------------------------------
    def close(self):
        pass

    #--------------------------------------------------------------------------
    def __iter__(self):
        """Return an iterator over crashes from RabbitMQ.

        Each crash is a tuple of the ``(args, kwargs)`` variety. The lone arg
        is a crash ID, and the kwargs contain only a callback function which
        the FTS app will call to send an ack to Rabbit after processing is
        complete.

        """
        for a_crash_id in self.crash_store.new_crashes():
            yield (
                (a_crash_id,),
                {'finished_func': partial(
                    self.crash_store.ack_crash,
                    a_crash_id
                )}
            )

    #--------------------------------------------------------------------------
    def __call__(self):
        return self.__iter__()
