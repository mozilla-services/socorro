# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use .env or environment
# variables.

import logging
import os
import re
import socket

from everett.manager import ConfigManager, ListOf, parse_bool
import dj_database_url

# NOTE(willkg): Need this on a separate line so we can ignore the unused import
from crashstats.settings.bundles import NPM_FILE_PATTERNS  # noqa
from crashstats.settings.bundles import PIPELINE_CSS, PIPELINE_JS

_config = ConfigManager.basic_config()

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# The socorro root is one directory above the webapp root
SOCORRO_ROOT = os.path.dirname(ROOT)


def path(*dirs):
    return os.path.join(ROOT, *dirs)


TOOL_ENV = _config(
    "TOOL_ENV",
    default="false",
    parser=parse_bool,
    doc=(
        "Whether or not we're running in a tool environment where we want to ignore "
        "required configuration"
    ),
)
if TOOL_ENV:
    fake_values = [
        ("ELASTICSEARCH_URL", "http://elasticsearch:9200"),
        ("SECRET_KEY", "ou812"),
    ]
    for key, val in fake_values:
        os.environ[key] = val


LOCAL_DEV_ENV = _config(
    "LOCAL_DEV_ENV",
    default="false",
    parser=parse_bool,
    doc="Whether or not we're running in the local development environment",
)

DEBUG = _config(
    "DEBUG",
    default="false",
    parser=parse_bool,
    doc=(
        "Debugging displays nice error messages, but leaks memory. Set this to false "
        "on all server instances and true only for development."
    ),
)

SITE_ID = 1

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Absolute path to the directory that holds media.
MEDIA_ROOT = path("media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
MEDIA_URL = "/media/"

STATIC_ROOT = _config(
    "STATIC_ROOT",
    default=path("static"),
    doc="Absolute path to the directory static files should be collected to.",
)

# URL prefix for static files
STATIC_URL = "/static/"

ALLOWED_HOSTS = _config("ALLOWED_HOSTS", default="", parser=ListOf(str))


# Defines the views served for root URLs.
ROOT_URLCONF = "crashstats.urls"

INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "pipeline",
    "corsheaders",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "django.contrib.admin.apps.SimpleAdminConfig",
    "mozilla_django_oidc",
    "rest_framework",
    # Socorro apps
    "crashstats.crashstats",
    "crashstats.api",
    "crashstats.authentication",
    "crashstats.cron",
    "crashstats.documentation",
    "crashstats.manage",
    "crashstats.monitoring",
    "crashstats.profile",
    "crashstats.signature",
    "crashstats.status",
    "crashstats.supersearch",
    "crashstats.tokens",
    "crashstats.topcrashers",
    "crashstats.sources",
    "django.contrib.messages",
    "waffle",
    "django_jinja",
]

MIDDLEWARE = [
    # CORS needs to go before other response-generating middlewares
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "crashstats.tokens.middleware.APIAuthenticationMiddleware",
    "mozilla_django_oidc.middleware.SessionRefresh",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # If you run crashstats behind a load balancer, your `REMOTE_ADDR` header
    # will be that of the load balancer instead of the actual user. The
    # solution is to instead rely on the `X-Real-IP' header set by nginx
    # module or something else.
    #
    # You ONLY want this if you know you can trust `X-Real-IP`. Make sure this
    # is *before* the `RatelimitMiddleware` middleware. Otherwise that
    # middleware is operating on the wrong value.
    "crashstats.crashstats.middleware.SetRemoteAddrFromRealIP",
    "csp.middleware.CSPMiddleware",
    "waffle.middleware.WaffleMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
    "crashstats.crashstats.middleware.Pretty400Errors",
]


# Allow inactive users to authenticate
# FIXME(Osmose): Remove this and the auto-logout code in favor of
# the default backend, which does not authenticate inactive users.
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.AllowAllUsersModelBackend",
    "mozilla_django_oidc.auth.OIDCAuthenticationBackend",
]


_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.template.context_processors.debug",
    "django.template.context_processors.media",
    "django.template.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "django.template.context_processors.request",
    "crashstats.crashstats.context_processors.settings",
    "crashstats.status.context_processors.status_message",
]

TEMPLATES = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": True,
        "OPTIONS": {
            # Use jinja2/ for jinja templates
            "app_dirname": "jinja2",
            # Don't figure out which template loader to use based on
            # file extension
            "match_extension": "",
            "context_processors": _CONTEXT_PROCESSORS,
            "undefined": "jinja2.Undefined",
            "extensions": [
                "jinja2.ext.do",
                "jinja2.ext.loopcontrols",
                # needed to avoid errors in django_jinja
                "jinja2.ext.i18n",
                "django_jinja.builtins.extensions.CsrfExtension",
                "django_jinja.builtins.extensions.StaticFilesExtension",
                "django_jinja.builtins.extensions.DjangoFiltersExtension",
                "pipeline.jinja2.PipelineExtension",
                "waffle.jinja.WaffleExtension",
            ],
            "globals": {},
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # what does this do?!
        "APP_DIRS": True,
        "OPTIONS": {"debug": DEBUG, "context_processors": _CONTEXT_PROCESSORS},
    },
]

LOGGING_LEVEL = _config(
    "LOGGING_LEVEL", default="INFO", doc="Logging level for Crash Stats code"
)

DJANGO_LOGGING_LEVEL = _config(
    "DJANGO_LOGGING_LEVEL",
    default="INFO",
    doc="Logging level for Django logging (requests, SQL, etc)",
)

HOSTNAME = _config(
    "HOSTNAME",
    default=socket.gethostname(),
    doc="Name of the host this is running on.",
)


class AddHostname(logging.Filter):
    def filter(self, record):
        record.hostname = HOSTNAME
        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"add_hostname": {"()": AddHostname}},
    "handlers": {
        "console": {
            "level": LOGGING_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "socorroapp",
        },
        "mozlog": {
            "level": LOGGING_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "mozlog",
            "filters": ["add_hostname"],
        },
    },
    "formatters": {
        "socorroapp": {
            "format": "%(asctime)s %(levelname)s - webapp - %(name)s - %(message)s"
        },
        "mozlog": {
            "()": "dockerflow.logging.JsonLogFormatter",
            "logger_name": "socorro",
        },
    },
}

if LOCAL_DEV_ENV:
    # In a local development environment, we don't want to see mozlog
    # format at all, but we do want to see markus things and py.warnings.
    # So set the logging up that way.
    LOGGING["loggers"] = {
        "django": {"handlers": ["console"], "level": DJANGO_LOGGING_LEVEL},
        "django.server": {"handlers": ["console"], "level": DJANGO_LOGGING_LEVEL},
        "django.request": {"handlers": ["console"], "level": DJANGO_LOGGING_LEVEL},
        "fillmore": {"handlers": ["console"], "level": logging.ERROR},
        "py.warnings": {"handlers": ["console"], "level": LOGGING_LEVEL},
        "markus": {"handlers": ["console"], "level": LOGGING_LEVEL},
        "crashstats": {"handlers": ["console"], "level": LOGGING_LEVEL},
    }
else:
    # In a server environment, we want to use mozlog format.
    LOGGING["loggers"] = {
        "django": {"handlers": ["mozlog"], "level": LOGGING_LEVEL},
        "django.server": {"handlers": ["mozlog"], "level": LOGGING_LEVEL},
        "crashstats": {"handlers": ["mozlog"], "level": LOGGING_LEVEL},
        "fillmore": {"handlers": ["mozlog"], "level": logging.ERROR},
        "markus": {"handlers": ["mozlog"], "level": logging.ERROR},
    }


REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]
}


# Link to source if possible
VCS_MAPPINGS = {
    "cvs": {
        "cvs.mozilla.org": (
            "http://bonsai.mozilla.org/cvsblame.cgi?file=%(file)s&rev=%(revision)s&mark=%(line)s#%(line)s"  # noqa
        )
    },
    "hg": {
        "hg.mozilla.org": (
            "https://hg.mozilla.org/%(repo)s/file/%(revision)s/%(file)s#l%(line)s"
        )
    },
    "git": {
        "git.mozilla.org": (
            "http://git.mozilla.org/?p=%(repo)s;a=blob;f=%(file)s;h=%(revision)s#l%(line)s"  # noqa
        ),
        "github.com": (
            "https://github.com/%(repo)s/blob/%(revision)s/%(file)s#L%(line)s"
        ),
    },
    "s3": {
        "gecko-generated-sources": (
            "/sources/highlight/?url=https://gecko-generated-sources.s3.amazonaws.com/%(file)s&line=%(line)s#L-%(line)s"  # noqa
        )
    },
}


# True if old legacy URLs we handle should be permanent 301 redirects.
# Transitionally it might be safer to set this to False as we roll out the new
# django re-write of Socorro.
PERMANENT_LEGACY_REDIRECTS = True

LOGIN_URL = "/login/"

# Use memcached for session storage
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# django-cors-headers should kick in for all API requests and support all origins
CORS_ALLOW_ALL_ORIGINS = True
CORS_URLS_REGEX = r"^/api/.*$"

# Process types to allow in queries.
# If tuple, the second option is human readable label.
PROCESS_TYPES = (
    "any",
    "parent",
    "plugin",
    "content",
    ("gpu", "GPU"),
    "all",  # alias for 'any'
)

# fields used in the simplified UI for Super Search
SIMPLE_SEARCH_FIELDS = ("product", "version", "platform", "process_type")

# the number of result filter on tcbs
TCBS_RESULT_COUNTS = (50, 100, 200, 300)

# channels allowed in middleware calls,
CHANNELS = ("release", "beta", "nightly", "esr")

# default channel
CHANNEL = "nightly"

# this is the max length of signatures in forms
SIGNATURE_MAX_LENGTH = 255

# We use django.contrib.messages for login, so let's use SessionStorage
# to avoid byte-big messages as cookies
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# A prefix that is sometimes prefixed on the crash ID when used elsewhere in
# the socorro eco-system.
CRASH_ID_PREFIX = "bp-"

# If true, allow robots to spider the site
ENGAGE_ROBOTS = False

BZAPI_BASE_URL = _config(
    "BZAPI_BASE_URL",
    default="https://bugzilla.mozilla.org/rest",
    doc="Base URL for Bugzilla API",
)

BZAPI_TOKEN = _config("BZAPI_TOKEN", default="", doc="Bugzilla API token")

# Base URL for Buildhub
BUILDHUB_BASE_URL = "https://buildhub.moz.tools/"

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
API_RATE_LIMIT = "100/m"
API_RATE_LIMIT_AUTHENTICATED = "1000/m"

# Rate limit when using the supersearch web interface
RATELIMIT_SUPERSEARCH = "10/m"
RATELIMIT_SUPERSEARCH_AUTHENTICATED = "100/m"

# Path to the view that gets executed if you hit upon a ratelimit block
RATELIMIT_VIEW = "crashstats.crashstats.views.ratelimit_blocked"

# To extend any settings from above here's an example:
# INSTALLED_APPS = base.INSTALLED_APPS + ['debug_toolbar']

# Recipients of traceback emails and other notifications.
ADMINS = [
    # ('Your Name', 'your_email@domain.com'),
]
MANAGERS = ADMINS

# ------------------------------------------------
# Below are settings that can be overridden using
# environment variables.

CACHE_IMPLEMENTATION_FETCHES = _config(
    "CACHE_IMPLEMENTATION_FETCHES", default="true", parser=parse_bool
)

# for local development these don't matter
STATSD_HOST = _config("STATSD_HOST", default="localhost", doc="statsd host.")
STATSD_PORT = _config("STATSD_PORT", default="8125", parser=int, doc="statsd port.")


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": _config("CACHE_LOCATION", default="127.0.0.1:11211"),
        "TIMEOUT": _config("CACHE_TIMEOUT", default="500", parser=int),
        "KEY_PREFIX": _config("CACHE_KEY_PREFIX", default="socorro"),
        "OPTIONS": {
            # Seconds to wait for send/recv calls
            "timeout": 5,
            # Seconds to wait for a connection to go through
            "connect_timeout": 5,
        },
    }
}

TIME_ZONE = _config("TIME_ZONE", default="UTC")

DATABASE_URL = _config("DATABASE_URL", default="sqlite://sqlite.crashstats.db")
DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}


STORAGES = {
    "staticfiles": {
        "BACKEND": "pipeline.storage.PipelineManifestStorage",
    },
}

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "npm.finders.NpmFinder",
    "pipeline.finders.PipelineFinder",
    # Make sure this comes last!
    "crashstats.crashstats.finders.LeftoverPipelineFinder",
]

PIPELINE = {
    "STYLESHEETS": PIPELINE_CSS,
    "JAVASCRIPT": PIPELINE_JS,
    "LESS_BINARY": _config("LESS_BINARY", default=path("node_modules/.bin/lessc")),
    "LESS_ARGUMENTS": (
        "--global-var=\"root-path='" + STATIC_ROOT + "/crashstats/css/'\""
    ),
    "JS_COMPRESSOR": "pipeline.compressors.uglifyjs.UglifyJSCompressor",
    "UGLIFYJS_BINARY": _config(
        "UGLIFYJS_BINARY", default=path("node_modules/.bin/uglifyjs")
    ),
    "UGLIFYJS_ARGUMENTS": "--mangle",
    "CSS_COMPRESSOR": "pipeline.compressors.cssmin.CSSMinCompressor",
    "CSSMIN_BINARY": _config("CSSMIN_BINARY", default=path("node_modules/.bin/cssmin")),
    # Don't wrap javascript code in... `(...code...)();`
    # because possibly much code has been built with the assumption that
    # things will be made available globally.
    "DISABLE_WRAPPER": True,
    "COMPILERS": ("pipeline.compilers.less.LessCompiler",),
    # The pipeline.jinja2.PipelineExtension extension doesn't support
    # automatically rendering any potentional compilation errors into
    # the rendered HTML, so just let it raise plain python exceptions.
    "SHOW_ERRORS_INLINE": False,
}

NPM_ROOT_PATH = _config("NPM_ROOT_PATH", default=ROOT)

SECRET_KEY = _config(
    "SECRET_KEY",
    doc="Make this unique, and don't share it with anybody. It cannot be blank.",
)

CSRF_COOKIE_NAME = "crashstatscsrfcookie"
CSRF_USE_SESSIONS = True

SESSION_COOKIE_SECURE = _config(
    "SESSION_COOKIE_SECURE",
    default="true",
    parser=parse_bool,
    doc=(
        "If you intend to run WITHOUT HTTPS, such as local development, "
        "then set this to false"
    ),
)

SESSION_COOKIE_HTTPONLY = _config(
    "SESSION_COOKIE_HTTPONLY",
    default="true",
    parser=parse_bool,
    doc="By default, use HTTPONLY cookies",
)

X_FRAME_OPTIONS = _config(
    "X_FRAME_OPTIONS",
    default="DENY",
    doc=(
        "By default, we don't want to be inside a frame. "
        "If you need to override this you can use the "
        "``django.views.decorators.clickjacking.xframe_options_sameorigin`` "
        "decorator on specific views that can be in a frame."
    ),
)

OVERVIEW_VERSION_URLS = _config(
    "OVERVIEW_VERSION_URLS",
    default="",
    doc="Comma-separated list of urls that serve version information in JSON format",
)

SENTRY_DSN = _config(
    "SENTRY_DSN",
    default="",
    doc="Sentry aggregates reports of uncaught errors and other events",
)

ANALYZE_MODEL_FETCHES = _config(
    "ANALYZE_MODEL_FETCHES",
    default="true",
    parser=parse_bool,
    doc="Set to true enable analysis of all model fetches",
)

# The list of valid rulesets for the Reprocessing API
# FIXME(willkg): we can pluck this from settings or structure
VALID_RULESETS = ["default", "regenerate_signature"]

# OIDC credentials are needed to be able to connect with OpenID Connect.
# Credentials for local development are set in /docker/config/oidcprovider-fixtures.json.
OIDC_RP_CLIENT_ID = _config("OIDC_RP_CLIENT_ID", default="")
OIDC_RP_CLIENT_SECRET = _config("OIDC_RP_CLIENT_SECRET", default="")
OIDC_OP_AUTHORIZATION_ENDPOINT = _config("OIDC_OP_AUTHORIZATION_ENDPOINT", default="")
OIDC_OP_TOKEN_ENDPOINT = _config("OIDC_OP_TOKEN_ENDPOINT", default="")
OIDC_OP_USER_ENDPOINT = _config("OIDC_OP_USER_ENDPOINT", default="")
# List of urls that are exempt from session refresh because they're used in XHR
# contexts and that doesn't handle redirecting.
OIDC_EXEMPT_URLS = [
    # Used by supersearch page as an XHR
    # data-fields-url
    "supersearch:search_fields",
    # data-results-url
    "supersearch:search_results",
    # Used by bugzilla.js
    "/buginfo/bug",
    # Used by signature report as an XHR
    # data-urls-summary
    "signature:signature_summary",
    # data-urls-reports
    "signature:signature_reports",
    # data-urls-bugzilla
    "signature:signature_bugzilla",
    # data-urls-comments
    "signature:signature_comments",
    # data-urls-correlations
    "signature:signature_correlations",
    # data-urls-graphs
    re.compile(r"^/signature/graphs/(?P<field>\w+)/$"),
    # data-urls-aggregations
    re.compile(r"^/signature/aggregation/(?P<aggregation>\w+)/$"),
]
LOGOUT_REDIRECT_URL = "/"

LAST_LOGIN_MAX = _config(
    "LAST_LOGIN_MAX",
    default=str(60 * 60 * 24),
    parser=int,
    doc=(
        "Max number of seconds you are allowed to be logged in with OAuth2. When the"
        "user has been logged in >= this number, the user is automatically logged out."
    ),
)

CSP_DEFAULT_SRC = ("'self'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = (
    "'self'",
    "data:",  # what jquery.tablesorter.js's CSS uses
)
CSP_CONNECT_SRC = ("'self'",)

CSP_REPORT_URI = ("/__cspreport__",)

NUMBER_OF_FEATURED_VERSIONS = _config(
    "NUMBER_OF_FEATURED_VERSIONS",
    default="4",
    parser=int,
    doc=(
        "This is the number of versions to display if a particular product "
        "has no 'featured versions'. Then we use the active versions, but capped "
        "up to this number."
    ),
)

VERSIONS_WINDOW_DAYS = _config(
    "VERSIONS_WINDOW_DAYS",
    default="60",
    parser=int,
    doc=(
        "Number of days to look at for versions in crash reports. This is set "
        "for two months. If we haven't gotten a crash report for some version in "
        "two months, then seems like that version isn't active."
    ),
)

VERSIONS_COUNT_THRESHOLD = _config(
    "VERSIONS_COUNT_THRESHOLD",
    default="50",
    parser=int,
    doc=(
        "Minimum number of crash reports in the VERSIONS_WINDOW_DAYS to be "
        "considered as a valid version."
    ),
)

# Prevents whitenoise from adding "Access-Control-Allow-Origin: *" header for static
# files. If we ever switch to hosting static assets on a CDN, we'll want to remove
# this.
WHITENOISE_ALLOW_ALL_ORIGINS = False
