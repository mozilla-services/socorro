import codecs
import os
from setuptools import setup, find_packages


# Prevent spurious errors during `python setup.py test`, a la
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html:
try:
    import multiprocessing
except ImportError:
    pass


def read(fname):
    fpath = os.path.join(os.path.dirname(__file__), fname)
    with codecs.open(fpath, 'r', 'utf8') as f:
        return f.read().strip()


def find_install_requires():
    return [x.strip() for x in
            read('requirements.txt').splitlines()
            if x.strip() and not x.startswith('#')]


setup(
    name='socorro',
    version='88',
    description=('Socorro is a server to accept and process Breakpad'
                 ' crash reports.'),
    long_description=open('README.md').read(),
    author='Mozilla',
    author_email='socorro-dev@mozilla.com',
    license='MPL',
    url='https://github.com/mozilla/socorro',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MPL License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        ],
    keywords=['socorro', 'breakpad', 'crash', 'reporting', 'minidump',
              'stacktrace'],
    packages=find_packages(),
    install_requires=find_install_requires(),
    entry_points={
        'console_scripts': [
            'socorro-setupdb = socorro.external.postgresql.setupdb_app:main'
            ],
        },
    test_suite='nose.collector',
    zip_safe=False,
),
