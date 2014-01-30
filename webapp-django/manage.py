#!/usr/bin/env python
import sys


from django.core.management import execute_manager, setup_environ

try:
    from kitsune import settings_local as settings
except ImportError:
    try:
        from crashstats import settings  # Assumed to be in the same directory.
    except ImportError:
        sys.stderr.write(
            "Error: Tried importing 'settings_local.py' and 'settings.py' "
            "but neither could be found (or they're throwing an ImportError)."
            " Please come back and try again later.")
        raise


# The first thing execute_manager does is call `setup_environ`. Logging config
# needs to access settings, so we'll setup the environ early.
setup_environ(settings)

if __name__ == "__main__":
    execute_manager(settings)
