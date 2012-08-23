## This is automatically imported by test-utils to make sure tests are run in
## a consistent way across different platforms and different developers.

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

CACHE_MIDDLEWARE = True
CACHE_MIDDLEWARE_FILES = False

BZAPI_BASE_URL = 'https://api-dev.bugzilla.muzilla.org/1.1'
