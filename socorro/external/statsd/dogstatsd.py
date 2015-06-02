# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datadog.dogstatsd import statsd


#==============================================================================
class StatsClient(object):
    """a wrapper around the datadog statsd client object to make it appear to
    have the same interface as the regular statsd client that we've been using
    """

    #--------------------------------------------------------------------------
    def __init__(self, host, port, prefix):
        statsd.host = host
        statsd.port = port
        self.prefix =  prefix

    #--------------------------------------------------------------------------
    def incr(self, name):
        return statsd.increment(name)

    #--------------------------------------------------------------------------
    def __getattr__(self, attr):
        return getattr(statsd, attr)

