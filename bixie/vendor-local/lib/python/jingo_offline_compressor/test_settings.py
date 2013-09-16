import os
import django

TEST_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tests')


COMPRESS_CACHE_BACKEND = 'locmem://'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = (
    'compressor',
    'jingo',
)

TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MEDIA_URL = '/media/'
STATIC_URL = MEDIA_URL


MEDIA_ROOT = os.path.join(TEST_DIR, 'media')

TEMPLATE_DIRS = (
    # Specifically choose a name that will not be considered
    # by app_directories loader, to make sure each test uses
    # a specific template without considering the others.
    os.path.join(TEST_DIR, 'test_templates'),
)

TEST_RUNNER = 'discover_runner.DiscoverRunner'

SECRET_KEY = "iufoj=mibkpdz*%bob952x(%49rqgv8gg45k36kjcg76&-y5=!"
