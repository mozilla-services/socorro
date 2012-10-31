# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use settings_local.py

from funfactory.settings_base import *

# Name of the top-level module where you put all your apps.
# If you did not install Playdoh with the funfactory installer script
# you may need to edit this value. See the docs about installing from a
# clone.
PROJECT_MODULE = 'crashstats'

# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

INSTALLED_APPS = list(INSTALLED_APPS) + [
    # Application base, containing global templates.
    '%s.base' % PROJECT_MODULE,
    # Example code. Can (and should) be removed for actual projects.
    '%s.crashstats' % PROJECT_MODULE,
    'jingo_offline_compressor',
    '%s.auth' % PROJECT_MODULE,
    'django_statsd',
    'django.contrib.messages',
]


# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:
JINGO_EXCLUDE_APPS = [
    'admin',
    'registration',
]

MIDDLEWARE_EXCLUDE_CLASSES = [
    'funfactory.middleware.LocaleURLMiddleware',
]

MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)

for app in MIDDLEWARE_EXCLUDE_CLASSES:
    if app in MIDDLEWARE_CLASSES:
        MIDDLEWARE_CLASSES.remove(app)

MIDDLEWARE_CLASSES = tuple(MIDDLEWARE_CLASSES) + (
    'django_statsd.middleware.GraphiteRequestTimingMiddleware',
    'django_statsd.middleware.GraphiteMiddleware',
)


STATSD_CLIENT = 'django_statsd.clients.normal'


# BrowserID configuration
AUTHENTICATION_BACKENDS = [
    'django_browserid.auth.BrowserIDBackend',
    'django.contrib.auth.backends.ModelBackend',
]

TEMPLATE_CONTEXT_PROCESSORS += (
    'crashstats.crashstats.context_processors.current_versions',
    'django_browserid.context_processors.browserid_form',
)

# Always generate a CSRF token for anonymous users.
ANON_ALWAYS = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'sqlite.crashstats.db',
    }
}

# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
DOMAIN_METHODS['messages'] = [
    ('%s/**.py' % PROJECT_MODULE,
        'tower.management.commands.extract.extract_tower_python'),
    ('%s/**/templates/**.html' % PROJECT_MODULE,
        'tower.management.commands.extract.extract_tower_template'),
    ('templates/**.html',
        'tower.management.commands.extract.extract_tower_template'),
],

# # Use this if you have localizable HTML files:
# DOMAIN_METHODS['lhtml'] = [
#    ('**/templates/**.lhtml',
#        'tower.management.commands.extract.extract_tower_template'),
# ]

# # Use this if you have localizable JS files:
# DOMAIN_METHODS['javascript'] = [
#    # Make sure that this won't pull in strings from external libraries you
#    # may use.
#    ('media/js/**.js', 'javascript'),
# ]

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
    'FennecAndroid': 'Firefox for Android'
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


# we can because we use jingo_offline_compressor
COMPRESS_OFFLINE = True

# True if old legacy URLs we handle should be permanent 301 redirects.
# Transitionally it might be safer to set this to False as we roll out the new
# django re-write of Socorro.
PERMANENT_LEGACY_REDIRECTS = True

# This is needed for BrowserID to work!
SITE_URL = 'http://localhost:8000'

LOGIN_URL = '/login/'
ALLOWED_PERSONA_EMAILS = (
    # fill this in in settings/local.py
)

# Use memcached for session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# we don't need bcrypt since we don't store real passwords
PWD_ALGORITHM = 'sha512'

# must be set but not applicable because we don't use bcrypt
HMAC_KEYS = {'any': 'thing'}

# Types of query that can be run in search
QUERY_TYPES = (
    'contains',
    'is_exactly',
    'starts_with',
    'simple'
)

# Maximum and default range of query that can be run in search
QUERY_RANGE_MAXIMUM_DAYS = 30
QUERY_RANGE_DEFAULT_DAYS = 14

# server to pull correlation data from
CORRELATION_SERVER = '//localhost:8000'
