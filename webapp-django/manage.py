#!/usr/bin/env python
import os

# Edit this if necessary or override the variable in your environment.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crashstats.settings')

from funfactory import manage


manage.setup_environ(__file__, more_pythonic=True)

if __name__ == "__main__":
    manage.main()
