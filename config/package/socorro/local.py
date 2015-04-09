# This is an example settings/local.py file.
# These settings overrides what's in settings/base.py

# To extend any settings from settings/base.py here's an example:
#from . import base
#INSTALLED_APPS = base.INSTALLED_APPS + ('debug_toolbar',)

ALLOWED_HOSTS = ['crash-stats']

CACHE_MIDDLEWARE = True
# creates "./models-cache" dir
# only applicable if CACHE_MIDDLEWARE is True
CACHE_MIDDLEWARE_FILES = False

# Socorro middleware instance to use
MWARE_BASE_URL = 'http://localhost'
MWARE_USERNAME = None
MWARE_PASSWORD = None
# HTTP/1.1 Host header to pass - in case this is a VHost
MWARE_HTTP_HOST = 'socorro-middleware'

DEFAULT_PRODUCT = 'WaterWolf'

# server to pull correlation data from
# CORRELATION_SERVER = 'https://crash-stats-dev.allizom.org'

# can be changed from null to log to test something locally
# or if using the debug toolbar, you might give toolbar a try
STATSD_CLIENT = 'django_statsd.clients.null'

# for local development these don't matter
#STATSD_HOST = 'localhost'
#STATSD_PORT = 8125
#STATSD_PREFIX = None

# Enable this to be able to run tests
# NB: Disable this caching mechanism in production environment as
# it will break work of anonymous CSRF if there is more than one
# web server thread.
# Comment out to use memcache from settings/base.py
#CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#        'LOCATION': 'crashstats'
#    }
#}

TIME_ZONE = 'UTC'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'breakpad',
        'USER': 'breakpad_rw',
        'PASSWORD': 'aPassword',
        'HOST': 'localhost',
        'PORT': '',
        'OPTIONS': {
        },
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    },
    # 'slave': {
    #     ...
    # },
}


# Uncomment this and set to all slave DBs in use on the site.
# SLAVE_DATABASES = ['slave']

# Recipients of traceback emails and other notifications.
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS

# Debugging displays nice error messages, but leaks memory. Set this to False
# on all server instances and True only for development.
DEBUG = TEMPLATE_DEBUG = False

# By default compression is done in runtime, if you enable
# offline compression, running the test suite will be 10 times faster
# but you'll need to remember to first run:
#     ./manage.py collectstatic --noinput
#     ./manage.py compress_jingo --force
# at least once every time any of the static files change.
COMPRESS_OFFLINE = True

# # Playdoh ships with sha512 password hashing by default. Bcrypt+HMAC is
# # safer, so it is recommended. Please read <http://git.io/0xqJPg>, then
# # switch this to bcrypt and pick a secret HMAC key for your application.
# PWD_ALGORITHM = 'bcrypt'
# HMAC_KEYS = {  # for bcrypt only
#     '2011-01-01': 'cheesecake',
# }

# Make this unique, and don't share it with anybody.  It cannot be blank.
SECRET_KEY = 'you must change this'

# Uncomment these to activate and customize Celery:
# CELERY_ALWAYS_EAGER = False  # required to activate celeryd
# BROKER_HOST = 'localhost'
# BROKER_PORT = 5672
# BROKER_USER = 'playdoh'
# BROKER_PASSWORD = 'playdoh'
# BROKER_VHOST = 'playdoh'
# CELERY_RESULT_BACKEND = 'amqp'

## Log settings

# SYSLOG_TAG = "http_app_playdoh"  # Make this unique to your project.
#import logging
#LOGGING = dict(loggers=dict(playdoh={'level': logging.DEBUG}))

# Common Event Format logging parameters
#CEF_PRODUCT = 'Playdoh'
#CEF_VENDOR = 'Mozilla'

# If you intend to run without HTTPS such as local development,
# then set this to False
SESSION_COOKIE_SECURE = False

# To get your Sentry key, go to https://errormill.mozilla.org/
#RAVEN_CONFIG = {
#    'dsn': ''  # see https://errormill.mozilla.org/
#}


# Specify the middleware implementation to use in the middleware
#SEARCH_MIDDLEWARE_IMPL = 'elasticsearch'

# If you intend to run with DEBUG=False, this must match the URL
# you're using
BROWSERID_AUDIENCES = ['http://crash-stats']

# Optional Google Analytics ID
#GOOGLE_ANALYTICS_ID = "UA-XXXXX-X"
# Root domain. Required iff you're providing an analytics ID.
#GOOGLE_ANALYTICS_DOMAIN = 'auto'

# Set to True enable analysis of all model fetches
#ANALYZE_MODEL_FETCHES = True

# If you crashstats behind a load balancer, your `REMOTE_ADDR` header
# will be that of the load balancer instead of the actual user.
# The solution is to instead rely on the `X-Forwarded-For` header.
# You ONLY want this if you know you can trust `X-Forwarded-For`.
# (Note! Make sure you uncomment the line `from . import base` at
# the top of this file first)
#base.MIDDLEWARE_CLASSES += (
#    'crashstats.crashstats.middleware.SetRemoteAddrFromForwardedFor',
#)

# Ensure that the uploaded file is effectively g+rw while preserving the group
# ownership inherited from system.
# See
# https://docs.djangoproject.com/en/dev/topics/http/\
#  file-uploads/#changing-upload-handler-behavior
#FILE_UPLOAD_PERMISSIONS = 0664

DATASERVICE_CONFIG_BASE = {
    'resource': {
        'postgresql': {
            'transaction_executor_class':
                'socorro.database.transaction_executor'
                '.TransactionExecutorWithLimitedBackoff',
            'backoff_delays': "0, 3",
        },
    },
    'secrets': {
        'postgresql': {
            'database_password': 'aPassword',
            'database_username': 'breakpad_rw',
        },
    }
}

# We don't want to test the migrations when we run tests.
# We trust that syncdb matches what you'd get if you install
# all the migrations.
SOUTH_TESTS_MIGRATE = False

# Credentials for being able to make an S3 connection
AWS_ACCESS_KEY = ''
AWS_SECRET_ACCESS_KEY = ''

# Information for uploading symbols to S3
SYMBOLS_BUCKET_DEFAULT_NAME = ''
# To set overriding exceptions by email, use:
SYMBOLS_BUCKET_EXCEPTIONS = {
    # e.g.
    # 'joe.bloggs@example.com': 'private-crashes.my-bucket'
    # or you can specify it as a tuple of (name, location)
    # 'joe@example.com': ('my-bucket', 'USWest1')
}
SYMBOLS_FILE_PREFIX = 'v1'
# e.g. "us-west-2" see boto.s3.connection.Location
# Only needed if the bucket has never been created
SYMBOLS_BUCKET_DEFAULT_LOCATION = None


