# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use .env or environment
# variables.

import logging
import os
import socket

from decouple import config, Csv
import dj_database_url

from crashstats.settings.bundles import NPM_FILE_PATTERNS, PIPELINE_CSS, PIPELINE_JS  # noqa
from socorro.lib.revision_data import get_version


ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        '..'
    ))

# The socorro root is one directory above the webapp root
SOCORRO_ROOT = os.path.dirname(ROOT)


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

# Whether or not we're running in the local development environment
LOCAL_DEV_ENV = config('LOCAL_DEV_ENV', False, cast=bool)

SITE_ID = 1

LANGUAGE_CODE = 'en-US'

# Absolute path to the directory that holds media.
MEDIA_ROOT = path('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = config('STATIC_ROOT', path('static'))

# URL prefix for static files
STATIC_URL = '/static/'

ALLOWED_HOSTS = config('ALLOWED_HOSTS', '', cast=Csv())


# Defines the views served for root URLs.
ROOT_URLCONF = 'crashstats.urls'

INSTALLED_APPS = (
    'pipeline',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'session_csrf',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'mozilla_django_oidc',

    # Socorro apps
    'crashstats.crashstats',
    'crashstats.api',
    'crashstats.authentication',
    'crashstats.cron',
    'crashstats.documentation',
    'crashstats.exploitability',
    'crashstats.manage',
    'crashstats.monitoring',
    'crashstats.profile',
    'crashstats.signature',
    'crashstats.status',
    'crashstats.supersearch',
    'crashstats.tokens',
    'crashstats.tools',
    'crashstats.topcrashers',
    'crashstats.sources',

    'django.contrib.messages',
    'raven.contrib.django.raven_compat',
    'waffle',
    'django_jinja',
)


MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware',
    'mozilla_django_oidc.middleware.SessionRefresh',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # If you run crashstats behind a load balancer, your `REMOTE_ADDR` header
    # will be that of the load balancer instead of the actual user. The
    # solution is to instead rely on the `X-Real-IP' header set by nginx
    # module or something else.
    #
    # You ONLY want this if you know you can trust `X-Real-IP`. Make sure this
    # is *before* the `RatelimitMiddleware` middleware. Otherwise that
    # middleware is operating on the wrong value.
    'crashstats.crashstats.middleware.SetRemoteAddrFromRealIP',

    'csp.middleware.CSPMiddleware',
    'waffle.middleware.WaffleMiddleware',
    'ratelimit.middleware.RatelimitMiddleware',
    'crashstats.tokens.middleware.APIAuthenticationMiddleware',
    'crashstats.crashstats.middleware.Pretty400Errors',
]


# Allow inactive users to authenticate
# FIXME(Osmose): Remove this and the auto-logout code in favor of
# the default backend, which does not authenticate inactive users.
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.AllowAllUsersModelBackend',
    'mozilla_django_oidc.auth.OIDCAuthenticationBackend',
)


_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.template.context_processors.debug',
    'django.template.context_processors.media',
    'django.template.context_processors.request',
    'session_csrf.context_processor',
    'django.contrib.messages.context_processors.messages',
    'django.template.context_processors.request',
    'crashstats.crashstats.context_processors.settings',
    'crashstats.status.context_processors.status_message',
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

LOGGING_LEVEL = config('LOGGING_LEVEL', 'INFO')

host_id = socket.gethostname()


class AddHostID(logging.Filter):
    def filter(self, record):
        record.host_id = host_id
        return True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'add_hostid': {
            '()': AddHostID
        },
    },
    'handlers': {
        'console': {
            'level': LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'socorroapp',
        },
        'mozlog': {
            'level': LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'mozlog',
            'filters': ['add_hostid']
        },
    },
    'formatters': {
        'socorroapp': {
            'format': '%(asctime)s %(levelname)s - %(name)s - %(message)s',
        },
        'mozlog': {
            '()': 'dockerflow.logging.JsonLogFormatter',
            'logger_name': 'socorro'
        },
    },
}

if LOCAL_DEV_ENV:
    # In a local development environment, we don't want to see mozlog
    # format at all, but we do want to see markus things and py.warnings.
    # So set the logging up that way.
    LOGGING['loggers'] = {
        'django': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
        },
        'django.server': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
        },
        'django.request': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
        },
        'py.warnings': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
        },
        'markus': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
        },
        'crashstats': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
        }
    }
else:
    # In a server environment, we want to use mozlog format.
    LOGGING['loggers'] = {
        'django': {
            'handlers': ['mozlog'],
            'level': LOGGING_LEVEL,
        },
        'django.server': {
            'handlers': ['mozlog'],
            'level': LOGGING_LEVEL,
        },
        'crashstats': {
            'handlers': ['mozlog'],
            'level': LOGGING_LEVEL,
        }
    }

# Some products have a different name in bugzilla and Socorro.
BUG_PRODUCT_MAP = {
    'FennecAndroid': 'Firefox for Android',
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
    },
    's3': {
        'gecko-generated-sources': (
            '/sources/highlight/?url=https://gecko-generated-so'
            'urces.s3.amazonaws.com/%(file)s&line=%(line)s#L-%(line)s'
        ),
    },
}


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
    50,
    100,
    200,
    300,
)

# channels allowed in middleware calls,
CHANNELS = (
    'release',
    'beta',
    'nightly',
    'esr'
)

# default channel
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
BZAPI_BASE_URL = config('BZAPI_BASE_URL', 'https://bugzilla.mozilla.org/rest')

# Base URL for Buildhub
BUILDHUB_BASE_URL = 'https://buildhub.moz.tools/'

# The index schema used in our elasticsearch databases, used in the
# Super Search Custom Query page.
ELASTICSEARCH_INDEX_SCHEMA = config('resource.elasticsearch.elasticsearch_index', 'socorro%Y%W')

# Number of shards per index in our Elasticsearch database.
ES_SHARDS_PER_INDEX = 10

# Default number of crashes to show on the Exploitable Crashes report
EXPLOITABILITY_BATCH_SIZE = config(
    'EXPLOITABILITY_BATCH_SIZE',
    default=250,
    cast=int
)

# Default number of days a token lasts until it expires
TOKENS_DEFAULT_EXPIRATION_DAYS = 90

# Store all dates timezone aware
USE_TZ = True

# Default for how many items to display in the admin batch tables
USERS_ADMIN_BATCH_SIZE = 10
EVENTS_ADMIN_BATCH_SIZE = 10
API_TOKENS_ADMIN_BATCH_SIZE = 10
STATUS_MESSAGE_ADMIN_BATCH_SIZE = 10

# Rate limit for when using the Web API for anonymous hits
API_RATE_LIMIT = '100/m'
API_RATE_LIMIT_AUTHENTICATED = '1000/m'

# Rate limit when using the supersearch web interface
RATELIMIT_SUPERSEARCH = '10/m'
RATELIMIT_SUPERSEARCH_AUTHENTICATED = '100/m'

# Path to the view that gets executed if you hit upon a ratelimit block
RATELIMIT_VIEW = 'crashstats.crashstats.views.ratelimit_blocked'

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

# ------------------------------------------------
# Below are settings that can be overridden using
# environment variables.

CACHE_IMPLEMENTATION_FETCHES = config(
    'CACHE_IMPLEMENTATION_FETCHES', True, cast=bool
)

DEFAULT_PRODUCT = config('DEFAULT_PRODUCT', 'Firefox')

# can be changed from null to log to test something locally
# or if using the debug toolbar, you might give toolbar a try
STATSD_CLIENT = config('STATSD_CLIENT', 'django_statsd.clients.null')

# for local development these don't matter
STATSD_HOST = config('STATSD_HOST', 'localhost')
STATSD_PORT = config('STATSD_PORT', 8125, cast=int)
STATSD_PREFIX = config('STATSD_PREFIX', None)

# set up markus backends for metrics
if LOCAL_DEV_ENV:
    MARKUS_BACKENDS = [
        {
            'class': 'markus.backends.logging.LoggingMetrics',
        },
        {
            'class': 'markus.backends.statsd.StatsdMetrics',
            'options': {
                'statsd_host': STATSD_HOST,
                'statsd_port': STATSD_PORT,
                'statsd_prefix': STATSD_PREFIX,
            }
        }
    ]
else:
    # Otherwise we're in a server environment and we use the datadog
    # backend there
    MARKUS_BACKENDS = [
        {
            # Log metrics to Datadog
            'class': 'markus.backends.datadog.DatadogMetrics',
            'options': {
                'statsd_host': STATSD_HOST,
                'statsd_port': STATSD_PORT,
                'statsd_namespace': STATSD_PREFIX,
            }
        }
    ]


CACHES = {
    'default': {
        'BACKEND': config(
            'CACHE_BACKEND',
            'django.core.cache.backends.memcached.MemcachedCache',
        ),
        'LOCATION': config('CACHE_LOCATION', '127.0.0.1:11211'),
        'TIMEOUT': config('CACHE_TIMEOUT', 500),
        'KEY_PREFIX': config('CACHE_KEY_PREFIX', 'socorro'),
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
    'npm.finders.NpmFinder',
    'pipeline.finders.PipelineFinder',
    # Make sure this comes last!
    'crashstats.crashstats.finders.LeftoverPipelineFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE = {
    'STYLESHEETS': PIPELINE_CSS,
    'JAVASCRIPT': PIPELINE_JS,
    'LESS_BINARY': config(
        'LESS_BINARY',
        path('node_modules/.bin/lessc')
    ),
    'LESS_ARGUMENTS': '--global-var="root-path=\'' + STATIC_ROOT + '/crashstats/css/\'"',
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
    ),
    # The pipeline.jinja2.PipelineExtension extension doesn't support
    # automatically rendering any potentional compilation errors into
    # the rendered HTML, so just let it raise plain python exceptions.
    'SHOW_ERRORS_INLINE': False,
}

NPM_ROOT_PATH = config('NPM_ROOT_PATH', ROOT)

# Make this unique, and don't share it with anybody.  It cannot be blank.
# FIXME remove this default when we are out of PHX
SECRET_KEY = config('SECRET_KEY', 'this must be changed!!')

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

SOCORRO_REVISION = get_version()

# Comma-separated list of urls that serve version information in JSON format
OVERVIEW_VERSION_URLS = config('OVERVIEW_VERSION_URLS', '')

# Raven sends errors to Sentry.
# The release is optional.
SENTRY_DSN = config('SENTRY_DSN', '')
if SENTRY_DSN:
    RAVEN_CONFIG = {
        'dsn': SENTRY_DSN,
        'release': SOCORRO_REVISION,
        # Defines keys to be sanitized by SanitizeKeysProcessor
        'sanitize_keys': [
            'sessionid',
            'csrftoken',
            'anoncsrf',
            'sc',
        ],
        'processors': (
            'raven.processors.SanitizeKeysProcessor',
            'raven.processors.SanitizePasswordsProcessor',
        )
    }

GOOGLE_ANALYTICS_ID = config('GOOGLE_ANALYTICS_ID', None)

# Set to True enable analysis of all model fetches
ANALYZE_MODEL_FETCHES = config('ANALYZE_MODEL_FETCHES', True, cast=bool)


# Credentials for being able to make an S3 connection
AWS_ACCESS_KEY = config('AWS_ACCESS_KEY', None)
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', None)
AWS_HOST = config('AWS_HOST', None)
AWS_PORT = config('AWS_PORT', 0, cast=int)
AWS_SECURE = config('AWS_SECURE', True, cast=bool)

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
        'boto': {
            'secret_access_key': config(
                'secrets.boto.secret_access_key',
                None
            ),
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
            'elasticsearch_index': ELASTICSEARCH_INDEX_SCHEMA,
            'elasticsearch_index_regex': config(
                'resource.elasticsearch.elasticsearch_index_regex', '^socorro[0-9]{6}$'
            )
        },
        'boto': {
            'access_key': config('resource.boto.access_key', None),
            'bucket_name': config('resource.boto.bucket_name', 'crashstats'),
            'region': config('resource.boto.region', 'us-west-2'),
            'prefix': config('resource.boto.prefix', ''),

            # NOTE(willkg): In the local dev environment, we need to use a
            # HostPortS3ConnectionContext which requires these additional configuration bits. The
            # defaults are taken from the config sections of the relevant classes.
            'resource_class': config(
                'resource.boto.resource_class',
                'socorro.external.boto.connection_context.RegionalS3ConnectionContext'
            ),
            'host': config('resource.boto.host', None),
            'port': config('resource.boto.port', None),
            'secure': config('resource.boto.secure', True),
            'calling_format': config(
                'resource.boto.calling_format', 'boto.s3.connection.OrdinaryCallingFormat'
            ),
        },
        'pubsub': {
            'service_account_file': config('resource.pubsub.service_account_file', None),
            'project_id': config('resource.pubsub.project_id', None),
            'standard_topic_name': config('resource.pubsub.standard_topic_name', None),
            'standard_subscription_name': config(
                'resource.pubsub.standard_subscription_name', None
            ),
            'priority_topic_name': config('resource.pubsub.priority_topic_name', None),
            'priority_subscription_name': config(
                'resource.pubsub.priority_subscription_name', None
            ),
            'reprocessing_topic_name': config('resource.pubsub.reprocessing_topic_name', None),
            'reprocessing_subscription_name': config(
                'resource.pubsub.reprocessing_subscription_name', None
            )
        }
    },
    'telemetrydata': {
        'bucket_name': config('TELEMETRY_BUCKET_NAME', None),
    }
}

# Configuration for the depcheck command
NPM_PATH = config('NPM_PATH', '/usr/bin/npm')
SAFETY_PATH = config('SAFETY_PATH', '/usr/local/bin/safety')
SAFETY_API_KEY = config('SAFETY_API_KEY', '')
PACKAGE_JSON_PATH = config('PACKAGE_JSON_PATH', '/app/webapp-django/package.json')

# OIDC credentials are needed to be able to connect with OpenID Connect.
# Credentials for local development are set in /docker/config/oidcprovider-fixtures.json.
OIDC_RP_CLIENT_ID = config('OIDC_RP_CLIENT_ID', '')
OIDC_RP_CLIENT_SECRET = config('OIDC_RP_CLIENT_SECRET', '')
OIDC_OP_AUTHORIZATION_ENDPOINT = config('OIDC_OP_AUTHORIZATION_ENDPOINT', '')
OIDC_OP_TOKEN_ENDPOINT = config('OIDC_OP_TOKEN_ENDPOINT', '')
OIDC_OP_USER_ENDPOINT = config('OIDC_OP_USER_ENDPOINT', '')
# List of urls that are exempt from session refresh because they're used in XHR
# contexts and that doesn't handle redirecting.
OIDC_EXEMPT_URLS = [
    # Used by supersearch page as an XHR
    '/search/fields/',
    '/search/results/',
    '/buginfo/bug',

    # Used by signature report as an XHR
    '/signature/summary/',
]
LOGOUT_REDIRECT_URL = '/'

# Max number of seconds you are allowed to be signed in with OAuth2.
# When the user has been signed in >= this number, the user is automatically
# signed out.
LAST_LOGIN_MAX = config(
    'LAST_LOGIN_MAX',
    default=60 * 60 * 24,
    cast=int
)


CSP_DEFAULT_SRC = (
    "'self'",
)
CSP_OBJECT_SRC = (
    "'none'",
)
CSP_SCRIPT_SRC = (
    "'self'",
    'https://apis.google.com',
    'https://www.google-analytics.com',
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    'https://code.cdn.mozilla.net',
)
CSP_IMG_SRC = (
    "'self'",
    'https://www.google-analytics.com',
    'https://secure.gravatar.com',
    'data:',  # what jquery.tablesorter.js's CSS uses
)
CSP_CONNECT_SRC = (
    "'self'",
)
CSP_FONT_SRC = (
    "'self'",
    'https://code.cdn.mozilla.net',
)

CSP_REPORT_URI = (
    '/__cspreport__',
)

# This is the number of versions to display if a particular product
# has no 'featured versions'. Then we use the active versions, but capped
# up to this number.
NUMBER_OF_FEATURED_VERSIONS = config('NUMBER_OF_FEATURED_VERSIONS', 4)
