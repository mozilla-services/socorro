# This is an example settings/local.py file.
# These settings overrides what's in settings/base.py

# To extend any settings from settings/base.py here's an example:
#from . import base
#INSTALLED_APPS = base.INSTALLED_APPS + ['debug_toolbar']

CACHE_MIDDLEWARE = False
# creates "./models-cache" dir
# only applicable if CACHE_MIDDLEWARE is True
CACHE_MIDDLEWARE_FILES = True

# Socorro middleware instance to use
MWARE_BASE_URL = 'http://socorro-api/bpapi'
MWARE_USERNAME = None
MWARE_PASSWORD = None
# HTTP/1.1 Host header to pass - in case this is a VHost
MWARE_HTTP_HOST = None

DEFAULT_PRODUCT = 'WaterWolf'

BZAPI_BASE_URL = 'https://api-dev.bugzilla.mozilla.org/1.1'

# server to pull correlation data from
# CORRELATION_SERVER = 'https://crash-stats-dev.allizom.org'

# can be changed from null to log to test something locally
# or if using the debug toolbar, you might give toolbar a try
STATSD_CLIENT = 'django_statsd.clients.null'

# for local development these don't matter
STATSD_HOST = 'localhost'
STATSD_PORT = 8125
STATSD_PREFIX = None

# Enable this to be able to run tests
# Comment out to use memcache from settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'crashstats'
    }
}

TIME_ZONE = 'UTC'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'breakpad',
        'USER': 'django',
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
DEBUG = TEMPLATE_DEBUG = True

# Is this a development instance? Set this to True on development/master
# instances and False on stage/prod.
DEV = True

# Use offline compression (requires jingo_compressor)
COMPRESS_OFFLINE = False

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
#SESSION_COOKIE_SECURE = False

# To get your Sentry key, go to https://errormill.mozilla.org/
#RAVEN_CONFIG = {
#    'dsn': ''  # see https://errormill.mozilla.org/
#}


# These must be set to be able log in
LDAP_BIND_DN = ''  # e.g. 'uid=binduser,ou=logins,dc=mozilla'
LDAP_BIND_PASSWORD = ''
# optionally...
#LDAP_SERVER_URI =
#LDAP_GROUP_NAMES =
#LDAP_GLOBAL_OPTIONS = {...}  # e.g. `{ldap.OPT_DEBUG_LEVEL: 4095}`

# if you want to debug logging in without belong to a real LDAP group...
#DEBUG_LDAP_EMAIL_ADDRESSES = [...]  # for debugging ONLY
