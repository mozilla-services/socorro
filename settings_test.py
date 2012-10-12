## This is automatically imported by test-utils to make sure tests are run in
## a consistent way across different platforms and different developers.

CACHE_MIDDLEWARE = True
CACHE_MIDDLEWARE_FILES = False

import os
os.environ['FORCE_DB'] = 'true'

BZAPI_BASE_URL = 'https://api-dev.bugzilla.muzilla.org/1.1'

# by scrubbing this to something unreal, we can be certain the tests never
# actually go out on the internet when `request.get` should always be mocked
MWARE_BASE_URL = 'http://shouldnotactuallybeused'

ALLOWED_PERSONA_EMAILS = (
    'kai@ro.com',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# see https://docs.djangoproject.com/en/1.4/topics/auth/#how-django-stores-passwords
# for how django stores passwords,
# To avoid depending on django_sha2 which requires bcrypt to be installed,
# we override whatever funfactory sets up.
# And because this is for running tests, we use the simplest hasher possible.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
