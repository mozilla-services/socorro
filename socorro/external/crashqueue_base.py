# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""This is the base of the crashqueue API for consuming and publishing
crash ids from queues for processing.
"""


class CrashQueueBase:
    """Base class for crash queue classes."""

    def close(self):
        pass

    def __iter__(self):
        """Return iterator over crash ids for processing.

        Each returned crash is a ``(crash_id, {kwargs})`` tuple with
        ``finished_func`` as the only key in ``kwargs``. The caller should call
        ``finished_func`` when it's done processing the crash.

        """
        pass

    def new_crashes(self):
        return self.__iter__()

    def __call__(self):
        return self.__iter__()

    def publish(self, queue, crash_ids):
        """Publish crash ids to specified queue."""
        assert queue in ["standard", "priority", "reprocessing"]
