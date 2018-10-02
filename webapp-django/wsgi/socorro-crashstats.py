from __future__ import print_function

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crashstats.settings')

from django.core.wsgi import get_wsgi_application  # noqa
application = get_wsgi_application()
