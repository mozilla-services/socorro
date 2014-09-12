# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use settings_local.py

from funfactory.settings_base import *

# This unset DATABASE_ROUTERS from funfactory because we're not
# interested in using multiple database for the webapp part.
DATABASE_ROUTERS = ()

# Name of the top-level module where you put all your apps.
# If you did not install Playdoh with the funfactory installer script
# you may need to edit this value. See the docs about installing from a
# clone.
PROJECT_MODULE = 'crashstats'

# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

INSTALLED_APPS = (
    'funfactory',
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
    # Example code. Can (and should) be removed for actual projects.
    '%s.crashstats' % PROJECT_MODULE,
    '%s.api' % PROJECT_MODULE,
    '%s.manage' % PROJECT_MODULE,
    '%s.supersearch' % PROJECT_MODULE,
    '%s.signature' % PROJECT_MODULE,
    '%s.auth' % PROJECT_MODULE,
    '%s.tokens' % PROJECT_MODULE,
    '%s.symbols' % PROJECT_MODULE,
    'django.contrib.messages',
    'raven.contrib.django.raven_compat',
    'waffle',
)


funfactory_JINJA_CONFIG = JINJA_CONFIG  # that from funfactory


def JINJA_CONFIG():
    # different from that in funfactory in that we don't want to
    # load the `tower` extension
    config = funfactory_JINJA_CONFIG()
    config['extensions'].remove('tower.template.i18n')
    return config


def COMPRESS_JINJA2_GET_ENVIRONMENT():
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
    '%s.tokens.middleware.APIAuthenticationMiddleware' % PROJECT_MODULE,
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
    'crashstats.base.context_processors.google_analytics',
    'crashstats.base.context_processors.browserid',
)

# Always generate a CSRF token for anonymous users.
ANON_ALWAYS = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'sqlite.crashstats.db',
    }
}

LOGGING = dict(loggers=dict(playdoh={'level': logging.DEBUG}))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        # fox2mike suggest to use IP instead of localhost
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 500,
        'KEY_PREFIX': 'crashstats',
    }
}

# Middleware related stuff
CACHE_MIDDLEWARE = True
CACHE_MIDDLEWARE_FILES = False  # store on filesystem instead of cache server

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

# top three operating systems
OPERATING_SYSTEMS = (
    'Linux',
    'Mac OS X',
    'Windows',
)

# Identifies nightly releases
NIGHTLY_RELEASE_TYPES = (
    'Aurora',
    'Nightly',
)


# No need to load it because we don't do i18n in this project
USE_I18N = False

# by default, compression is done in runtime.
COMPRESS_OFFLINE = False

# True if old legacy URLs we handle should be permanent 301 redirects.
# Transitionally it might be safer to set this to False as we roll out the new
# django re-write of Socorro.
PERMANENT_LEGACY_REDIRECTS = True

LOGIN_URL = '/login/'

# Use memcached for session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# The default, is to be secure. This requires that you run your socorro
# instance over HTTPS. If you don't (e.g. local development) override
# this in settings/local.py to False.
SESSION_COOKIE_SECURE = True

# we don't need bcrypt since we don't store real passwords
PWD_ALGORITHM = 'sha512'

# must be set but not applicable because we don't use bcrypt
HMAC_KEYS = {'any': 'thing'}

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
EXPLOITABILITY_BATCH_SIZE = 250

# Default number of days to show in explosive crashes reports
EXPLOSIVE_REPORT_DAYS = 10

# how many seconds to sleep when getting a ConnectionError
MIDDLEWARE_RETRY_SLEEPTIME = 3

# how many times to re-attempt on ConnectionError after some sleep
MIDDLEWARE_RETRIES = 10

# Overridden so we can control the redirects better
BROWSERID_VERIFY_CLASS = '%s.auth.views.CustomBrowserIDVerify' % PROJECT_MODULE

# For a more friendly Persona pop-up
BROWSERID_REQUEST_ARGS = {'siteName': 'Mozilla Crash Reports'}

# Analyze all model fetches
ANALYZE_MODEL_FETCHES = False

# Default number of days a token lasts until it expires
TOKENS_DEFAULT_EXPIRATION_DAYS = 90

# Store all dates timezone aware
USE_TZ = True

# Default for how many users to display in the Users Admin UI
USERS_ADMIN_BATCH_SIZE = 10

# Individual strings that can't be allowed in any of the lines in the
# content of a symbols archive file.
DISALLOWED_SYMBOLS_SNIPPETS = (
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1012672
    'qcom/proprietary',
)

# Rate limit for when using the Web API for anonymous hits
API_RATE_LIMIT = '10/m'

# When we pull platforms from the Platforms API we later decide which of
# these to display at various points in the UI.
DISPLAY_OS_NAMES = ['Windows', 'Mac OS X', 'Linux']
