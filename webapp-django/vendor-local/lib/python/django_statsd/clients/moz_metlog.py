from statsd.client import StatsClient
from django.conf import settings


class StatsClient(StatsClient):
    """A client that pushes messages to metlog """

    def __init__(self, *args, **kw):
        super(StatsClient, self).__init__(*args, **kw)
        if getattr(settings, 'METLOG', None) is None:
            raise AttributeError(
                    "Metlog needs to be configured as settings.METLOG")

        self.metlog = settings.METLOG

    def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        self.metlog.timer_send(stat, delta, rate=rate)

    def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        self.metlog.incr(stat, count, rate=rate)

    def decr(self, stat, count=1, rate=1):
        """Decrement a stat by `count`."""
        self.metlog.incr(stat, -count, rate=rate)
