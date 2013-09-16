import logging

from statsd.client import StatsClient

log = logging.getLogger('statsd')


class StatsClient(StatsClient):
    """A client that pushes things into a local cache."""

    def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        log.info('Timing: %s, %s, %s' % (stat, delta, rate))

    def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        log.info('Increment: %s, %s, %s' % (stat, count, rate))

    def decr(self, stat, count=1, rate=1):
        """Decrement a stat by `count`."""
        log.info('Decrement: %s, %s, %s' % (stat, count, rate))
