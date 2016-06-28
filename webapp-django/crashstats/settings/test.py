"""
When you run tests with `./manage.py test` these settings are ALWAYS
imported last and overrides any other base or environment variable
settings.

The purpose of this is to guarantee that certain settings are always
set for test suite runs no matter what you do on the local system.

Ultimately, it helps make sure you never actually use real URLs. For
example, if a test incorrectly doesn't mock `requests.get()` for
example, it shouldn't actually try to reach out to a real valid URL.
"""

CACHE_MIDDLEWARE = True

DEFAULT_PRODUCT = 'WaterWolf'

# here we deliberately "destroy" the BZAPI URL so running tests that are
# badly mocked never accidentally actually use a real working network address
BZAPI_BASE_URL = 'https://bugzilla.testrunner/rest'

# by scrubbing this to something unreal, we can be certain the tests never
# actually go out on the internet when `request.get` should always be mocked
MWARE_BASE_URL = 'http://shouldnotactuallybeused.com'

STATSD_CLIENT = 'django_statsd.clients.null'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Because this is for running tests, we use the simplest hasher possible.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)


# don't accidentally send anything to sentry whilst running tests
RAVEN_CONFIG = {}
SENTRY_DSN = None


BROWSERID_AUDIENCES = ['http://testserver']

# Make sure these have something but something not right
# so the tests never accidentally manage to connect to AWS
# for realz.
AWS_ACCESS_KEY = 'something'
AWS_SECRET_ACCESS_KEY = 'anything'
SYMBOLS_BUCKET_DEFAULT_NAME = 'my-lovely-bucket'
SYMBOLS_FILE_PREFIX = 'v99'
SYMBOLS_BUCKET_DEFAULT_LOCATION = 'us-west-2'


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

MIDDLEWARE_RETRIES = 10
MIDDLEWARE_MIDDLEWARE_RETRY_SLEEPTIME = 3

# During testing, if mocking isn't done right, we never want to
# accidentally send data to Google Analytics.
GOOGLE_ANALYTICS_API_URL = 'https://example.com/collect'
# By default, unset the GOOGLE_ANALYTICS_ID
GOOGLE_ANALYTICS_ID = None
# Forcibly setting this to be what the default is in settings/base.py
# so that local settings don't break tests.
GOOGLE_ANALYTICS_DOMAIN = 'auto'


# During testing we want to pretend that we've set up the OAuth2
# credentials.
OAUTH2_CLIENT_ID = '12345-example.apps.googleusercontent.com'
OAUTH2_CLIENT_SECRET = 'somethingsomethingsecret'
OAUTH2_VALID_ISSUERS = ['accounts.example.com']
