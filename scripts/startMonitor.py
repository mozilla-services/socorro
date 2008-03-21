#! /usr/bin/env python

import socorro.monitor
import socorro.config as config

socorro.monitor.startMonitor()

print >>config.statusReportStream, "Done."




