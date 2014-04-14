from time import time

from statsd.client import StatsClient


class StatsClient(StatsClient):
    """A client that pushes things into a local cache."""

    def __init__(self, *args, **kw):
        super(StatsClient, self).__init__(*args, **kw)
        self.reset()

    def reset(self):
        self.cache = {}
        self.timings = []

    def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        stat = '%s|timing' % stat
        now = time() * 1000
        self.timings.append([stat, now, delta, now + delta])

    def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        stat = '%s|count' % stat
        self.cache.setdefault(stat, [])
        self.cache[stat].append([count, rate])

    def decr(self, stat, count=1, rate=1):
        """Decrement a stat by `count`."""
        stat = '%s|count' % stat
        self.cache.setdefault(stat, [])
        self.cache[stat].append([-count, rate])

    def _send(self, stat, value, rate):
        pass
