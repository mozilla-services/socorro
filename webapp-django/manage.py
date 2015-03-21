#!/usr/bin/env python
import os
import warnings

# Edit this if necessary or override the variable in your environment.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crashstats.settings')

from funfactory import manage

# re-enable deprecation warnings per https://code.djangoproject.com/ticket/18985
warnings.simplefilter("default", DeprecationWarning)
manage.setup_environ(__file__, more_pythonic=True)

if __name__ == "__main__":
    manage.main()
