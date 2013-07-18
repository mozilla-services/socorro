from django.conf import settings
from django.utils.importlib import import_module

# Workaround for tests.
try:
    patches = getattr(settings, 'STATSD_PATCHES', [])
except ImportError:
    patches = []

for patch in patches:
    import_module(patch).patch()
