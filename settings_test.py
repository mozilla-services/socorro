## This is automatically imported by test-utils to make sure tests are run in
## a consistent way across different platforms and different developers.

CACHE_MIDDLEWARE = True
CACHE_MIDDLEWARE_FILES = False

BZAPI_BASE_URL = 'https://api-dev.bugzilla.muzilla.org/1.1'

# by scrubbing this to something unreal, we can be certain the tests never
# actually go out on the internet when `request.get` should always be mocked
MWARE_BASE_URL = 'http://shouldnotactuallybeused'
