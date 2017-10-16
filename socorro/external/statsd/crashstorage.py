# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# flake8: noqa

# FIXME(willkg): These are for friendly-namespace, but we should probably get rid of them or at
# least keep the original names.
from socorro.external.statsd.statsd_base import (
    StatsdCounter as StatsdCrashStorage,
)
from socorro.external.statsd.statsd_base import (
    StatsdBenchmarkingWrapper as StatsdBenchmarkingCrashStorage,
)
