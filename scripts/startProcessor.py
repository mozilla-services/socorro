#! /usr/bin/env python

import socorro.externalProcessor
import socorro.config as config

p = socorro.externalProcessor.ProcessorWithExternalBreakpad()
p.start()
print >>config.statusReportStream, "Done."



