"""
Settings for running tests. These override settings in base.py.
"""

from crashstats.settings.base import *  # noqa

CACHE_IMPLEMENTATION_FETCHES = True

DEFAULT_PRODUCT = 'WaterWolf'

# here we deliberately "destroy" the BZAPI URL so running tests that are
# badly mocked never accidentally actually use a real working network address
BZAPI_BASE_URL = 'https://bugzilla.testrunner/rest'

STATSD_CLIENT = 'django_statsd.clients.null'

SECRET_KEY = 'fakekey'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'crashstats',
        'OPTIONS': {
            'MAX_ENTRIES': 2000,  # Avoid culling during tests
        },
    }
}

# Because this is for running tests, we use the simplest hasher possible.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)


# don't accidentally send anything to sentry whilst running tests
RAVEN_CONFIG = {}
SENTRY_DSN = None


# Make sure these have something but something not right
# so the tests never accidentally manage to connect to AWS
# for realz.
AWS_ACCESS_KEY = 'something'
AWS_SECRET_ACCESS_KEY = 'anything'
SYMBOLS_BUCKET_DEFAULT_NAME = 'my-lovely-bucket'
SYMBOLS_FILE_PREFIX = 'v99'
SYMBOLS_BUCKET_DEFAULT_LOCATION = 'us-west-2'
# We want AWS to use connect_to_region, so we make AWS_HOST an empty string
AWS_HOST = ''


# Test-specific Socorro configuration
SOCORRO_IMPLEMENTATIONS_CONFIG = {
    'resource': {
        'elasticsearch': {
            'elasticsearch_urls': ['http://example:9123'],
        },
        'boto': {
            'bucket_name': 'crashstats-test'
        }
    },
    'telemetrydata': {
        'bucket_name': 'telemetry-test'
    }
}

# Remove SessionRefresh middleware so that tests don't need to have a non-expired OIDC token
MIDDLEWARE.remove('mozilla_django_oidc.middleware.SessionRefresh') # noqa
