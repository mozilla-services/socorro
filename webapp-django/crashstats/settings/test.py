"""
Settings for running tests. These override settings in base.py.
"""

from crashstats.settings.base import *  # noqa

CACHE_IMPLEMENTATION_FETCHES = True

DEFAULT_PRODUCT = 'WaterWolf'

# here we deliberately "destroy" the BZAPI URL so running tests that are
# badly mocked never accidentally actually use a real working network address
BZAPI_BASE_URL = 'https://bugzilla.testrunner/rest'

# by scrubbing this to something unreal, we can be certain the tests never
# actually go out on the internet when `request.get` should always be mocked
MWARE_BASE_URL = 'http://shouldnotactuallybeused.com'

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
        'LOCATION': 'crashstats'
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


# So it never ever actually uses a real ElasticSearch server
SOCORRO_IMPLEMENTATIONS_CONFIG = {
    'resource': {
        'elasticsearch': {
            'elasticsearch_urls': ['http://example:9123'],
        },
    }
}


# Make sure we never actually hit a real URL when testing the
# Crash-analysis monitoring.
CRASH_ANALYSIS_URL = 'https://crashanalysis.m.c/something/'
CRASH_ANALYSIS_MONITOR_DAYS_BACK = 2

# During testing, if mocking isn't done right, we never want to
# accidentally send data to Google Analytics.
GOOGLE_ANALYTICS_API_URL = 'https://example.com/collect'
# By default, unset the GOOGLE_ANALYTICS_ID
GOOGLE_ANALYTICS_ID = None


# During testing we want to pretend that we've set up the OAuth2
# credentials.
OAUTH2_CLIENT_ID = '12345-example.apps.googleusercontent.com'
OAUTH2_CLIENT_SECRET = 'somethingsomethingsecret'
OAUTH2_VALID_ISSUERS = ['accounts.example.com']
