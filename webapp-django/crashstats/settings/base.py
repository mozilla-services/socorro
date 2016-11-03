# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use .env or environment
# variables.

import os
import logging
from pkg_resources import resource_string

import dj_database_url
from decouple import config, Csv

from bundles import PIPELINE_CSS, PIPELINE_JS


ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        '..'
    ))


def path(*dirs):
    return os.path.join(ROOT, *dirs)

# Debugging displays nice error messages, but leaks memory. Set this to False
# on all server instances and True only for development.
DEBUG = config('DEBUG', False, cast=bool)

# Set this to True to make debugging AJAX requests easier; development-only!
DEBUG_PROPAGATE_EXCEPTIONS = config(
    'DEBUG_PROPAGATE_EXCEPTIONS',
    False,
    cast=bool
)


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


ALLOWED_HOSTS = config('ALLOWED_HOSTS', '', cast=Csv())


# Name of the top-level module where you put all your apps.
PROJECT_MODULE = 'crashstats'

# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

INSTALLED_APPS = (
    'pipeline',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django_nose',
    'session_csrf',

    # Application base, containing global templates.
    '%s.base' % PROJECT_MODULE,

    # Other Socorro apps.
    '%s.crashstats' % PROJECT_MODULE,
    '%s.api' % PROJECT_MODULE,
    '%s.authentication' % PROJECT_MODULE,
    '%s.documentation' % PROJECT_MODULE,
    '%s.home' % PROJECT_MODULE,
    '%s.manage' % PROJECT_MODULE,
    '%s.monitoring' % PROJECT_MODULE,
    '%s.profile' % PROJECT_MODULE,
    '%s.signature' % PROJECT_MODULE,
    '%s.status' % PROJECT_MODULE,
    '%s.supersearch' % PROJECT_MODULE,
    '%s.symbols' % PROJECT_MODULE,
    '%s.tokens' % PROJECT_MODULE,
    '%s.tools' % PROJECT_MODULE,
    '%s.topcrashers' % PROJECT_MODULE,

    'django.contrib.messages',
    'raven.contrib.django.raven_compat',
    'waffle',
    'eventlog',
    'django_jinja',
)


TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'waffle.middleware.WaffleMiddleware',
    'ratelimit.middleware.RatelimitMiddleware',
    '%s.tokens.middleware.APIAuthenticationMiddleware' % PROJECT_MODULE,
    '%s.crashstats.middleware.Propagate400Errors' % PROJECT_MODULE,
    '%s.crashstats.middleware.Pretty400Errors' % PROJECT_MODULE,
)


_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'session_csrf.context_processor',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    '%s.authentication.context_processors.oauth2' % PROJECT_MODULE,
    '%s.base.context_processors.debug' % PROJECT_MODULE,
    '%s.status.context_processors.status_message' % PROJECT_MODULE,
    '%s.crashstats.context_processors.help_urls' % PROJECT_MODULE,
)

TEMPLATES = [
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'APP_DIRS': True,
        'OPTIONS': {
            # Use jinja2/ for jinja templates
            'app_dirname': 'jinja2',
            # Don't figure out which template loader to use based on
            # file extension
            'match_extension': '',
            # 'newstyle_gettext': True,
            'context_processors': _CONTEXT_PROCESSORS,
            'undefined': 'jinja2.Undefined',
            'extensions': [
                'jinja2.ext.do',
                'jinja2.ext.loopcontrols',
                'jinja2.ext.with_',
                'jinja2.ext.i18n',  # needed to avoid errors in django_jinja
                'jinja2.ext.autoescape',
                'django_jinja.builtins.extensions.CsrfExtension',
                'django_jinja.builtins.extensions.StaticFilesExtension',
                'django_jinja.builtins.extensions.DjangoFiltersExtension',
                'pipeline.jinja2.PipelineExtension',
                'waffle.jinja.WaffleExtension',
            ],
            'globals': {}
        }
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # what does this do?!
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': _CONTEXT_PROCESSORS,
        }
    },
]

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
        'hg.mozilla.org': ('https://hg.mozilla.org/%(repo)s'
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

# Process types to allow in queries.
# If tuple, the second option is human readable label.
PROCESS_TYPES = (
    'any',
    'browser',
    'plugin',
    'content',
    ('gpu', 'GPU'),
    'all',  # alias for 'any'
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
ENGAGE_ROBOTS = False

# Base URL for when we use the Bugzilla API
BZAPI_BASE_URL = 'https://bugzilla.mozilla.org/rest'

# The index schema used in our elasticsearch databases, used in the
# Super Search Custom Query page.
ELASTICSEARCH_INDEX_SCHEMA = 'socorro%Y%W'

# Number of shards per index in our Elasticsearch database.
ES_SHARDS_PER_INDEX = 5

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

# Default number of days a token lasts until it expires
TOKENS_DEFAULT_EXPIRATION_DAYS = 90

# Store all dates timezone aware
USE_TZ = True

# Default for how many items to display in the admin batch tables
USERS_ADMIN_BATCH_SIZE = 10
EVENTS_ADMIN_BATCH_SIZE = 10
API_TOKENS_ADMIN_BATCH_SIZE = 10
SYMBOLS_UPLOADS_ADMIN_BATCH_SIZE = 10
STATUS_MESSAGE_ADMIN_BATCH_SIZE = 10

# Individual strings that can't be allowed in any of the lines in the
# content of a symbols archive file.
DISALLOWED_SYMBOLS_SNIPPETS = (
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1012672
    'qcom/proprietary',
)

# Rate limit for when using the Web API for anonymous hits
API_RATE_LIMIT = '100/m'
API_RATE_LIMIT_AUTHENTICATED = '1000/m'

# Rate limit when using the supersearch web interface
RATELIMIT_SUPERSEARCH = '10/m'
RATELIMIT_SUPERSEARCH_AUTHENTICATED = '100/m'

# Path to the view that gets executed if you hit upon a ratelimit block
RATELIMIT_VIEW = '%s.crashstats.views.ratelimit_blocked' % PROJECT_MODULE

# When we pull platforms from the Platforms API we later decide which of
# these to display at various points in the UI.
DISPLAY_OS_NAMES = ['Windows', 'Mac OS X', 'Linux']

# When this is true, every 400 Bad Request error we get from the middleware
# is propagated onto the client who caused the request in the webapp.
PROPAGATE_MIDDLEWARE_400_ERRORS = True

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


# We'll possible reuse this later in this file
database_url = config(
    'DATABASE_URL',
    'sqlite://sqlite.crashstats.db',
)

DATABASES = {
    'default': dj_database_url.parse(database_url)
}

# Uncomment this and set to all slave DBs in use on the site.
SLAVE_DATABASES = config('SLAVE_DATABASES', '', cast=Csv())


STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE = {
    'STYLESHEETS': PIPELINE_CSS,
    'JAVASCRIPT': PIPELINE_JS,
    'LESS_BINARY': config(
        'LESS_BINARY',
        path('node_modules/.bin/lessc')
    ),
    'JS_COMPRESSOR': 'pipeline.compressors.uglifyjs.UglifyJSCompressor',
    'UGLIFYJS_BINARY': config(
        'UGLIFYJS_BINARY',
        path('node_modules/.bin/uglifyjs')
    ),
    'UGLIFYJS_ARGUMENTS': '--mangle',
    'CSS_COMPRESSOR': 'pipeline.compressors.cssmin.CSSMinCompressor',
    'CSSMIN_BINARY': config(
        'CSSMIN_BINARY',
        path('node_modules/.bin/cssmin')
    ),
    # Don't wrap javascript code in... `(...code...)();`
    # because possibly much code has been built with the assumption that
    # things will be made available globally.
    'DISABLE_WRAPPER': True,
    'COMPILERS': (
        'pipeline.compilers.less.LessCompiler',
        'crashstats.crashstats.pipelinecompilers.GoogleAnalyticsCompiler',
    ),
    # The pipeline.jinja2.PipelineExtension extension doesn't support
    # automatically rendering any potentional compilation errors into
    # the rendered HTML, so just let it raise plain python exceptions.
    'SHOW_ERRORS_INLINE': False,
}

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

# By default, use HTTPONLY cookies
SESSION_COOKIE_HTTPONLY = config('SESSION_COOKIE_HTTPONLY', True, cast=bool)

# By default, we don't want to be inside a frame.
# If you need to override this you can use the
# `django.views.decorators.clickjacking.xframe_options_sameorigin`
# decorator on specific views that can be in a frame.
X_FRAME_OPTIONS = config('X_FRAME_OPTIONS', 'DENY')

# When socorro is installed (python setup.py install), it will create
# a file in site-packages for socorro called "socorro/socorro_revision.txt".
# If this socorro was installed like that, let's pick it up and use it.
try:
    SOCORRO_REVISION = resource_string('socorro', 'socorro_revision.txt')
except IOError:
    SOCORRO_REVISION = None

# Raven sends errors to Sentry.
# The release is optional.
raven_dsn = config('RAVEN_DSN', '')
if raven_dsn:
    RAVEN_CONFIG = {
        'dsn': raven_dsn,
        'release': SOCORRO_REVISION,
    }

# The Mozilla Google Analytics ID is used here as a default.
# The reason is that our deployment (when it runs `./manage.py collectstatic`)
# runs before the environment variables have been all set.
# See https://bugzilla.mozilla.org/show_bug.cgi?id=1314258
GOOGLE_ANALYTICS_ID = config('GOOGLE_ANALYTICS_ID', 'UA-35433268-50')

# Set to True enable analysis of all model fetches
ANALYZE_MODEL_FETCHES = config('ANALYZE_MODEL_FETCHES', False, cast=bool)


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

# Set to the default Mozilla Socorro uses
SYMBOLS_BUCKET_DEFAULT_LOCATION = config(
    'SYMBOLS_BUCKET_DEFAULT_LOCATION',
    'us-west-2'
)

# This `IMPLEMENTATIONS_DATABASE_URL` is optional. By default, the
# implementation classes will use the config coming from `DATABASE_URL`.
# For local development you might want to connect to different databases
# for the Django ORM and for the socorro implementation classes.
implementations_database_url = config(
    'IMPLEMENTATIONS_DATABASE_URL',
    '',
)
if not implementations_database_url:
    implementations_database_url = database_url
implementations_config = dj_database_url.parse(
    implementations_database_url
)

# Config for when the models pull directly from socorro.external classes.
SOCORRO_IMPLEMENTATIONS_CONFIG = {
    'secrets': {
        'postgresql': {
            'database_password': implementations_config['PASSWORD'],
            'database_username': implementations_config['USER'],
        },
        'rabbitmq': {
            'rabbitmq_user': config('RABBITMQ_USER', ''),
            'rabbitmq_password': config('RABBITMQ_PASSWORD', ''),
        },
        'boto': {
            'secret_access_key': config('secrets.boto.secret_access_key', ''),
        },
    },
    'resource': {
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
        },
        'postgresql': {
            'database_hostname': implementations_config['HOST'],
            'database_name': implementations_config['NAME'],
            'database_port': implementations_config['PORT'],
        },
        'rabbitmq': {
            'host': config('RABBITMQ_HOST', 'localhost'),
            'virtual_host': config('RABBITMQ_VIRTUAL_HOST', '/'),
            'port': config('RABBITMQ_PORT', 5672),
        },
        'boto': {
            'access_key': config('resource.boto.access_key', ''),
            'bucket_name': config(
                'resource.boto.bucket_name', 'crashstats'),
            'prefix': config('resource.boto.prefix', ''),
            'keybuilder_class': config(
                'resource.boto.keybuilder_class',
                'socorro.external.boto.connection_context.DatePrefixKeyBuilder'
            ),
        }
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

# URL to send the Google Analytics pageviews and event tracking.
# The value of this is extremely unlikely to change any time soon,
GOOGLE_ANALYTICS_API_URL = config(
    'GOOGLE_ANALYTICS_API_URL',
    'https://ssl.google-analytics.com/collect'
)

# If calls to the Google Analytics API are done asynchronously, this
# value can be quite high (5-10 seconds).
GOOGLE_ANALYTICS_API_TIMEOUT = config(
    'GOOGLE_ANALYTICS_API_TIMEOUT',
    5,  # seconds
    cast=int
)

# OAuth2 credentials are needed to be able to connect with Google OpenID
# Connect. Credentials can be retrieved from the
# Google Developers Console at
# https://console.developers.google.com/apis/credentials
OAUTH2_CLIENT_ID = config(
    'OAUTH2_CLIENT_ID',
    ''
)
OAUTH2_CLIENT_SECRET = config(
    'OAUTH2_CLIENT_SECRET',
    ''
)

OAUTH2_VALID_ISSUERS = config(
    'OAUTH2_VALID_ISSUERS',
    default='accounts.google.com',
    cast=Csv()
)

# Max number of seconds you are allowed to be signed in with OAuth2.
# When the user has been signed in >= this number, the user is automatically
# signed out.
LAST_LOGIN_MAX = config(
    'LAST_LOGIN_MAX',
    default=60 * 60 * 24,
    cast=int
)


GOOGLE_AUTH_HELP_URL = 'https://wiki.mozilla.org/Socorro/GoogleAuth'
