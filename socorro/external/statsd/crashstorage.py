# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import markus

from socorro.external.crashstorage_base import CrashStorageBase


class MetricsCounter(CrashStorageBase):
    """Counts the number of times it's called"""

    def __init__(
        self,
        metrics_prefix="",
        active_list=["save_processed_crash", "act"],
    ):
        """
        :arg metrics_prefix: a string to be used as the prefix for metrics keys
        :arg active_list: list of counters that are enabled
        """
        self.metrics_prefix = metrics_prefix
        self.active_list = active_list
        self.metrics = markus.get_metrics(metrics_prefix)

    def _make_key(self, *args):
        return ".".join(x for x in args if x)

    def __getattr__(self, attr):
        if attr in self.active_list:
            self.metrics.incr(attr)
        return self._noop

    def _noop(self, *args, **kwargs):
        pass
