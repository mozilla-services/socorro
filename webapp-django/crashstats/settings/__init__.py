"""
By default, crashstats.settings.base has the defaults, but within that file
those defaults are overwritten by reading from the environment.
Lastly, all settings in crashstats.settings.test overrides lastly meaning,
if specified in crashstats.settings.test, that it doesn't matter what's
in crashstats.settings.base or the environment.
This makes tests more predictable because we can avoid local settings
as much as possible.
"""

import sys

from .base import *  # NOQA


if len(sys.argv) > 1 and sys.argv[1] == 'test':
    import logging
    logging.disable(logging.CRITICAL)  # Shuts up logging when running tests
    from .test import *  # NOQA
