import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crashstats.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


try:
    import newrelic.agent
except ImportError:
    newrelic = False


if newrelic:
    newrelic_ini = os.getenv('NEWRELIC_PYTHON_INI_FILE', None)
    if newrelic_ini:
        if os.path.isfile(newrelic_ini):
            newrelic.agent.initialize(newrelic_ini)
            application = newrelic.agent.wsgi_application()(application)
        else:
            print >>sys.stderr, (
                "NEWRELIC_PYTHON_INI_FILE set but file does not exist. "
                "Skipping to initialize newrelic agent."
            )
