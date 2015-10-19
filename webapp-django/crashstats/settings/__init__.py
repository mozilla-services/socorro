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

# TODO remove this whole try/except when we can safely stop using local.py
try:
    from .local import *  # NOQA
    import warnings
    warnings.warn(
        "Use environment variables or a .env file instead of local.py",
        DeprecationWarning
    )
except ImportError:
    pass


if len(sys.argv) > 1 and sys.argv[1] == 'test':
    from .test import *  # NOQA
