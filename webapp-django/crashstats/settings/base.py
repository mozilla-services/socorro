# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use .env or environment
# variables.

import os
import logging

import dj_database_url
from decouple import config, Csv


ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        '..'
    ))


def path(*dirs):
    return os.path.join(ROOT, *dirs)


SITE_ID = 1

LANGUAGE_CODE = 'en-US'

# Absolute path to the directory that holds media.
MEDIA_ROOT = path('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = path('static')

# URL prefix for static files
STATIC_URL = '/static/'


TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    path('templates'),
)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', '', cast=Csv())


# Name of the top-level module where you put all your apps.
PROJECT_MODULE = 'crashstats'

# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

INSTALLED_APPS = (
    'compressor',
    'django_browserid',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'commonware.response.cookies',
    'django_nose',
    'session_csrf',

    # Application base, containing global templates.
    '%s.base' % PROJECT_MODULE,

    # Other Socorro apps.
    '%s.dataservice' % PROJECT_MODULE,
    '%s.crashstats' % PROJECT_MODULE,
    '%s.api' % PROJECT_MODULE,
    '%s.manage' % PROJECT_MODULE,
    '%s.supersearch' % PROJECT_MODULE,
    '%s.signature' % PROJECT_MODULE,
    '%s.topcrashers' % PROJECT_MODULE,
    '%s.authentication' % PROJECT_MODULE,
    '%s.tokens' % PROJECT_MODULE,
    '%s.symbols' % PROJECT_MODULE,
    '%s.profile' % PROJECT_MODULE,
    '%s.monitoring' % PROJECT_MODULE,

    'django.contrib.messages',
    'raven.contrib.django.raven_compat',
    'waffle',
    'eventlog',
)


TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

COMPRESS_ROOT = STATIC_ROOT

COMPRESS_CSS_FILTERS = (
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter'
)

COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)


def JINJA_CONFIG():
    config = {
        'extensions': [
            'jinja2.ext.do',
            'jinja2.ext.with_',
            'jinja2.ext.loopcontrols'
        ],
        'finalize': lambda x: x if x is not None else '',
    }
    return config


def COMPRESS_JINJA2_GET_ENVIRONMENT():
    """This function is automatically called by django-compressor"""
    from jingo import env
    from compressor.contrib.jinja2ext import CompressorExtension
    env.add_extension(CompressorExtension)

    return env


# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:
JINGO_EXCLUDE_APPS = (
    'browserid',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'commonware.middleware.FrameOptionsHeader',

    'waffle.middleware.WaffleMiddleware',
    'ratelimit.middleware.RatelimitMiddleware',
    '%s.tokens.middleware.APIAuthenticationMiddleware' % PROJECT_MODULE,
    '%s.crashstats.middleware.Propagate400Errors' % PROJECT_MODULE,
)


# BrowserID configuration
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_browserid.auth.BrowserIDBackend',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'session_csrf.context_processor',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    '%s.base.context_processors.google_analytics' % PROJECT_MODULE,
    '%s.base.context_processors.browserid' % PROJECT_MODULE,
)

# Always generate a CSRF token for anonymous users.
ANON_ALWAYS = True

LOG_LEVEL = logging.INFO

HAS_SYSLOG = True  # XXX needed??

LOGGING_CONFIG = None

# This disables all mail_admins on all django.request errors.
# We can do this because we use Sentry now instead
LOGGING = {
    'loggers': {
        'django.request': {
            'handlers': []
        }
    }
}

# Some products have a different name in bugzilla and Socorro.
BUG_PRODUCT_MAP = {
    'FennecAndroid': 'Firefox for Android',
    'B2G': 'Firefox OS',
}

# Link to source if possible
VCS_MAPPINGS = {
    'cvs': {
        'cvs.mozilla.org': ('http://bonsai.mozilla.org/cvsblame.cgi?'
                            'file=%(file)s&rev=%(revision)s&'
                            'mark=%(line)s#%(line)s')
    },
    'hg': {
        'hg.mozilla.org': ('http://hg.mozilla.org/%(repo)s'
                           '/annotate/%(revision)s/%(file)s#l%(line)s')
    },
    'git': {
        'git.mozilla.org': ('http://git.mozilla.org/?p=%(repo)s;a=blob;'
                            'f=%(file)s;h=%(revision)s#l%(line)s'),
        'github.com': ('https://github.com/%(repo)s/blob/%(revision)s/'
                       '%(file)s#L%(line)s')
    }
}

# Identifies nightly releases
NIGHTLY_RELEASE_TYPES = (
    'Aurora',
    'Nightly',
)


# No need to load it because we don't do i18n in this project
USE_I18N = False

USE_L10N = False

# True if old legacy URLs we handle should be permanent 301 redirects.
# Transitionally it might be safer to set this to False as we roll out the new
# django re-write of Socorro.
PERMANENT_LEGACY_REDIRECTS = True

LOGIN_URL = '/login/'

# Use memcached for session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Types of query that can be run in search
QUERY_TYPES = (
    'contains',
    'is_exactly',
    'starts_with',
    'simple',
    'exact',  # for backward compatibility
    'startswith',  # for backward compatibility
)

# This is for backward compatibility with the PHP app.
QUERY_TYPES_MAP = {
    'exact': 'is_exactly',
    'startswith': 'starts_with',
}

# Maximum and default range of query that can be run in search
QUERY_RANGE_MAXIMUM_DAYS = 30
QUERY_RANGE_MAXIMUM_DAYS_ADMIN = 120
QUERY_RANGE_DEFAULT_DAYS = 14

# range unit values to allow in queries
RANGE_UNITS = (
    'weeks',
    'days',
    'hours',
)

# process types to allow in queries
PROCESS_TYPES = (
    'any',
    'browser',
    'plugin',
    'content',
    'all',  # alias for 'any'
)

# hang types to allow in queries
HANG_TYPES = (
    'any',
    'crash',
    'hang',
    'all',  # alias for 'any'
)

# plugin fields to allow in queries
PLUGIN_FIELDS = (
    'filename',
    'name',
)

# fields used in the simplified UI for Super Search
SIMPLE_SEARCH_FIELDS = (
    'product',
    'version',
    'platform',
    'process_type',
)

# the number of result filter on tcbs
TCBS_RESULT_COUNTS = (
    '50',
    '100',
    '200',
    '300'
)

# channels allowed in middleware calls,
# such as adu by signature
CHANNELS = (
    'release',
    'beta',
    'aurora',
    'nightly',
    'esr'
)

# default channel for adu by signature graph
CHANNEL = 'nightly'

# this is the max length of signatures in forms
SIGNATURE_MAX_LENGTH = 255

# We use django.contrib.messages for login, so let's use SessionStorage
# to avoid byte-big messages as cookies
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'


# A prefix that is sometimes prefixed on the crash ID when used elsewhere in
# the socorro eco-system.
CRASH_ID_PREFIX = 'bp-'


# If true, allow robots to spider the site
ENGAGE_ROBOTS = config(
    'ENGAGE_ROBOTS',
    default=False,
    cast=bool,
)

# Base URL for when we use the Bugzilla API
BZAPI_BASE_URL = 'https://bugzilla.mozilla.org/rest'

# Specify the middleware implementation to use in the middleware
# Leave empty to use the default
SEARCH_MIDDLEWARE_IMPL = None

# The index schema used in our elasticsearch databases, used in the
# Super Search Custom Query page.
ELASTICSEARCH_INDEX_SCHEMA = 'socorro%Y%W'

# Valid type for correlations reports
CORRELATION_REPORT_TYPES = (
    'core-counts',
    'interesting-addons',
    'interesting-addons-with-versions',
    'interesting-modules',
    'interesting-modules-with-versions'
)

# Default number of crashes to show on the Exploitable Crashes report
EXPLOITABILITY_BATCH_SIZE = config(
    'EXPLOITABILITY_BATCH_SIZE',
    default=250,
    cast=int
)

# Default number of days to show in explosive crashes reports
EXPLOSIVE_REPORT_DAYS = 10

# how many seconds to sleep when getting a ConnectionError
MIDDLEWARE_RETRY_SLEEPTIME = config(
    'MIDDLEWARE_RETRY_SLEEPTIME',
    default=3,
    cast=int,
)

# how many times to re-attempt on ConnectionError after some sleep
MIDDLEWARE_RETRIES = config(
    'MIDDLEWARE_RETRIES',
    default=10,
    cast=int,
)

# Overridden so we can control the redirects better
BROWSERID_VERIFY_CLASS = (
    '%s.authentication.views.CustomBrowserIDVerify' % PROJECT_MODULE
)

# For a more friendly Persona pop-up
BROWSERID_REQUEST_ARGS = {'siteName': 'Mozilla Crash Reports'}

# Default number of days a token lasts until it expires
TOKENS_DEFAULT_EXPIRATION_DAYS = 90

# Store all dates timezone aware
USE_TZ = True

# Default for how many items to display in the admin batch tables
USERS_ADMIN_BATCH_SIZE = 10
EVENTS_ADMIN_BATCH_SIZE = 10
API_TOKENS_ADMIN_BATCH_SIZE = 10
SYMBOLS_UPLOADS_ADMIN_BATCH_SIZE = 10

# Individual strings that can't be allowed in any of the lines in the
# content of a symbols archive file.
DISALLOWED_SYMBOLS_SNIPPETS = (
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1012672
    'qcom/proprietary',
)

# Rate limit for when using the Web API for anonymous hits
API_RATE_LIMIT = '100/m'

# Rate limit when using the supersearch web interface
RATELIMIT_SUPERSEARCH = '10/m'

# Path to the view that gets executed if you hit upon a ratelimit block
RATELIMIT_VIEW = '%s.crashstats.views.ratelimit_blocked' % PROJECT_MODULE

# When we pull platforms from the Platforms API we later decide which of
# these to display at various points in the UI.
DISPLAY_OS_NAMES = ['Windows', 'Mac OS X', 'Linux']

# When this is true, every 400 Bad Request error we get from the middleware
# is propagated onto the client who caused the request in the webapp.
PROPAGATE_MIDDLEWARE_400_ERRORS = True

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
            'database_username': 'test',
        },
    }
}

# We don't want to test the migrations when we run tests.
# We trust that syncdb matches what you'd get if you install
# all the migrations.
SOUTH_TESTS_MIGRATE = False

# To extend any settings from above here's an example:
# INSTALLED_APPS = base.INSTALLED_APPS + ['debug_toolbar']

# Recipients of traceback emails and other notifications.
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS

# import logging
# LOGGING = dict(loggers=dict(playdoh={'level': logging.DEBUG}))

# If you run crashstats behind a load balancer, your `REMOTE_ADDR` header
# will be that of the load balancer instead of the actual user.
# The solution is to instead rely on the `X-Forwarded-For` header.
# You ONLY want this if you know you can trust `X-Forwarded-For`.
# (Note! Make sure you uncomment the line `from . import base` at
# the top of this file first)
# base.MIDDLEWARE_CLASSES += (
#     'crashstats.crashstats.middleware.SetRemoteAddrFromForwardedFor',
# )

# When you don't have permission to upload Symbols you might be confused
# what to do next. On the page that explains that you don't have permission
# there's a chance to put a link
# SYMBOLS_PERMISSION_HINT_LINK = {
#     'url': 'https://bugzilla.mozilla.org/enter_bug.cgi?product=Socorro&'
#            'component=General&groups=client-services-security',
#     'label': 'File a bug in bugzilla'
# }

# To change the configuration for any dataservice object, you may set
# parameters in the DATASERVICE_CONFIG_BASE which is used by dataservice
# app. Detailed config is documented in each dataservice object imported
# by the app.
#
# Below is an example of changing the api_whitelist for the Bugs service
# We convert the dict to a string, as configman prefers a string here.
# import json
# DATASERVICE_CONFIG_BASE.update({
#     'services': {
#         'Bugs': {
#             'api_whitelist': json.dumps({
#                 'hits': ('id','signature',)
#             })
#         }
#     }
# })

# to override the content-type of specific file extensinos:
SYMBOLS_MIME_OVERRIDES = {
    'sym': 'text/plain'
}
SYMBOLS_COMPRESS_EXTENSIONS = config(
    'SYMBOLS_COMPRESS_EXTENSIONS',
    'sym',
    cast=Csv()
)

# ------------------------------------------------
# Below are settings that can be overridden using
# environment variables.

CACHE_MIDDLEWARE = config('CACHE_MIDDLEWARE', True, cast=bool)
# creates "./models-cache" dir
# only applicable if CACHE_MIDDLEWARE is True
CACHE_MIDDLEWARE_FILES = config('CACHE_MIDDLEWARE_FILES', False, cast=bool)

# Socorro middleware instance to use
MWARE_BASE_URL = config('MWARE_BASE_URL', 'http://localhost:5200')
MWARE_USERNAME = config('MWARE_USERNAME', None)
MWARE_PASSWORD = config('MWARE_PASSWORD', None)
# HTTP/1.1 Host header to pass - in case this is a VHost
MWARE_HTTP_HOST = config('MWARE_HTTP_HOST', None)

DEFAULT_PRODUCT = config('DEFAULT_PRODUCT', 'WaterWolf')

# can be changed from null to log to test something locally
# or if using the debug toolbar, you might give toolbar a try
STATSD_CLIENT = config('STATSD_CLIENT', 'django_statsd.clients.null')

# for local development these don't matter
STATSD_HOST = config('STATSD_HOST', 'localhost')
STATSD_PORT = config('STATSD_PORT', 8125, cast=int)
STATSD_PREFIX = config('STATSD_PREFIX', None)

# Enable this to be able to run tests
# NB: Disable this caching mechanism in production environment as
# it will break work of anonymous CSRF if there is more than one
# web server thread.
# Comment out to use memcache from settings/base.py
CACHES = {
    'default': {
        # use django.core.cache.backends.locmem.LocMemCache for prod
        'BACKEND': config(
            'CACHE_BACKEND',
            'django.core.cache.backends.memcached.MemcachedCache',
        ),
        # fox2mike suggest to use IP instead of localhost
        'LOCATION': config('CACHE_LOCATION', '127.0.0.1:11211'),
        'TIMEOUT': config('CACHE_TIMEOUT', 500),
        'KEY_PREFIX': config('CACHE_KEY_PREFIX', 'crashstats'),
    }
}

TIME_ZONE = config('TIME_ZONE', 'UTC')

# Only use the old way of settings DATABASES IF you haven't fully migrated yet
if (
    not config('DATABASE_URL', None) and (
        config('DATABASE_ENGINE', None) or
        config('DATABASE_NAME', None) or
        config('DATABASE_USER', None) or
        config('DATABASE_PASSWORD', None) or
        config('DATABASE_PORT', None)
    )
):
    # Database credentials set up the old way
    import warnings
    warnings.warn(
        "Use DATABASE_URL instead of depending on DATABASE_* settings",
        DeprecationWarning
    )
    DATABASES = {
        'default': {
            # use django.db.backends.postgresql_psycopg for production
            'ENGINE': config('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
            'NAME': config('DATABASE_NAME', 'sqlite.crashstats.db'),
            'USER': config('DATABASE_USER', ''),
            'PASSWORD': config('DATABASE_PASSWORD', ''),
            'HOST': config('DATABASE_HOST', ''),
            'PORT': config('DATABASE_PORT', ''),
            'OPTIONS': {
            },
            # 'TEST_CHARSET': 'utf8',
            # 'TEST_COLLATION': 'utf8_general_ci',
        },
        # 'slave': {
        #     ...
        # },
    }
else:
    DATABASES = {
        'default': config(
            'DATABASE_URL',
            'sqlite://sqlite.crashstats.db',
            cast=dj_database_url.parse
        )
    }

# Uncomment this and set to all slave DBs in use on the site.
SLAVE_DATABASES = config('SLAVE_DATABASES', '', cast=Csv())

# Debugging displays nice error messages, but leaks memory. Set this to False
# on all server instances and True only for development.
DEBUG = TEMPLATE_DEBUG = config('DEBUG', False, cast=bool)

# Set this to True to make debugging AJAX requests easier; development-only!
DEBUG_PROPAGATE_EXCEPTIONS = config(
    'DEBUG_PROPAGATE_EXCEPTIONS',
    False,
    cast=bool
)

COMPRESS_ENABLED = config('COMPRESS_ENABLED', True, cast=bool)

# By default compression is done in runtime, if you enable
# offline compression, running the test suite will be 10 times faster
# but you'll need to remember to first run:
#     ./manage.py collectstatic --noinput
#     ./manage.py compress --force --engine=jinja2
# at least once every time any of the static files change.
COMPRESS_OFFLINE = config('COMPRESS_OFFLINE', True, cast=bool)

COMPRESS_ROOT = STATIC_ROOT
COMPRESS_CSS_FILTERS = (
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter'
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

# Make this unique, and don't share it with anybody.  It cannot be blank.
# FIXME remove this default when we are out of PHX
SECRET_KEY = config('SECRET_KEY', 'this must be changed!!')

# Log settings

# Make this unique to your project.
SYSLOG_TAG = config('SYSLOG_TAG', 'http_app_playdoh')

# Common Event Format logging parameters
CEF_PRODUCT = config('CEF_PRODUCT', 'Playdoh')
CEF_VENDOR = config('CEF_VENDOR', 'Mozilla')

# If you intend to run WITHOUT HTTPS, such as local development,
# then set this to False
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', True, cast=bool)

# To get your Sentry key, go to https://errormill.mozilla.org/
RAVEN_CONFIG = {
    'dsn': config('RAVEN_DSN', '')  # see https://errormill.mozilla.org/
}


# Specify the middleware implementation to use in the middleware
SEARCH_MIDDLEWARE_IMPL = config('SEARCH_MIDDLEWARE_IMPL', 'elasticsearch')

# If you intend to run with DEBUG=False, this must match the URL
# you're using
BROWSERID_AUDIENCES = config(
    'BROWSERID_AUDIENCES',
    'http://localhost:8000',
    cast=Csv()
)

# Optional Google Analytics ID (UA-XXXXX-X)
GOOGLE_ANALYTICS_ID = config('GOOGLE_ANALYTICS_ID', None)
# Root domain. Required iff you're providing an analytics ID.
GOOGLE_ANALYTICS_DOMAIN = config('GOOGLE_ANALYTICS_DOMAIN', 'auto')

# Set to True enable analysis of all model fetches
ANALYZE_MODEL_FETCHES = config('ANALYZE_MODEL_FETCHES', False, cast=bool)


# Dataservice API configuration
# Extend dataservices settings from settings/base.py here
# At a minimum, you'll probably want to change db username/password. All
# dataservice objects inherit resource configuration and so can all
# have their database resource configuration set once in 'secrets.postgresql'
# and 'resource.postgresql' keys.
DATASERVICE_CONFIG_BASE.update({
    'secrets': {
        'postgresql': {
            'database_password': config(
                'DATASERVICE_DATABASE_PASSWORD',
                'aPassword'
            ),
            'database_username': config(
                'DATASERVICE_DATABASE_USERNAME',
                'breakpad_rw'
            ),
            'database_hostname': config(
                'DATASERVICE_DATABASE_HOSTNAME',
                'localhost'
            ),
            'database_name': config(
                'DATASERVICE_DATABASE_NAME',
                'breakpad'
            ),
            'database_port': config(
                'DATASERVICE_DATABASE_PORT',
                '5432'
            ),
        }
    }
})


# Credentials for being able to make an S3 connection
AWS_ACCESS_KEY = config('AWS_ACCESS_KEY', '')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', '')

# Information for uploading symbols to S3
SYMBOLS_BUCKET_DEFAULT_NAME = config('SYMBOLS_BUCKET_DEFAULT_NAME', '')

# The format for this is `email:bucketname, email2:bucketname, etc`
SYMBOLS_BUCKET_EXCEPTIONS = config('SYMBOLS_BUCKET_EXCEPTIONS', '', cast=Csv())
SYMBOLS_BUCKET_EXCEPTIONS = dict(
    x.strip().split(':', 1) for x in SYMBOLS_BUCKET_EXCEPTIONS
)
# We *used* to allow just one single key/value override exceptions
# we need to continue to support for a little bit.
if (
    config('SYMBOLS_BUCKET_EXCEPTIONS_USER', '') and
    config('SYMBOLS_BUCKET_EXCEPTIONS_BUCKET', '')
):
    import warnings
    warnings.warn(
        'Note! To specify exceptions for users for different buckets, '
        'instead use the CSV based key SYMBOLS_BUCKET_EXCEPTIONS where '
        'each combination is written as \'emailregex:bucketname\' and '
        'multiples are written as comma separated.',
        DeprecationWarning
    )
    SYMBOLS_BUCKET_EXCEPTIONS[
        config('SYMBOLS_BUCKET_EXCEPTIONS_USER', '')
    ] = config('SYMBOLS_BUCKET_EXCEPTIONS_BUCKET', '')


SYMBOLS_FILE_PREFIX = config('SYMBOLS_FILE_PREFIX', 'v1')
# e.g. "us-west-2" see boto.s3.connection.Location
# Only needed if the bucket has never been created
SYMBOLS_BUCKET_DEFAULT_LOCATION = config(
    'SYMBOLS_BUCKET_DEFAULT_LOCATION',
    None
)

# Config for when the models pull directly from socorro.external classes.
# NOTE: This is overwritten, for tests in crashstats.settings.test
SOCORRO_IMPLEMENTATIONS_CONFIG = {
    'elasticsearch': {
        # All of these settings are repeated with sensible defaults
        # in the implementation itself.
        # We repeat them here so it becomes super easy to override
        # from the way we set settings for the webapp.
        'elasticsearch_urls': config(
            'ELASTICSEARCH_URLS',
            'http://localhost:9200',
            cast=Csv()
        ),
        # e.g. (deliberately commented out)
        # 'elasticsearch_doctype': config(
        #     'ELASTICSEARCH_DOCTYPE',
        #     'crash_reports'
        # )
    }
}

# On the report list page, we show correlations.
# We show one set of accordions per product & OS & version combo.
# How many combos we show (sorted by those with most # crashes) is
# determined by this setting:
MAX_CORRELATION_COMBOS_PER_SIGNATURE = 1

CRASH_ANALYSIS_URL = 'https://crash-analysis.mozilla.com/crash_analysis/'

# At what point do we consider crontabber to be stale.
# Ie. if it hasn't run for a certain number of minutes we'd consider
# that a failing situation and it'll trigger monitoring.
CRONTABBER_STALE_MINUTES = config(
    'CRONTABBER_STALE_MINUTES',
    # We have a lot of jobs that run every 1 hour, in case some job
    # takes a very long time to finish, we'll bump this up a bit
    # to a higher default.
    default=60 * 2
)
