# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import codecs
import glob
import os

from setuptools import find_packages, setup


def read(fname):
    fpath = os.path.join(os.path.dirname(__file__), fname)
    with codecs.open(fpath, "r", "utf8") as f:
        return f.read().strip()


setup(
    name="socorro",
    version="1.0.0",
    description="Socorro is a server to accept and process Breakpad crash reports.",
    long_description=open("README.rst").read(),
    author="Mozilla",
    author_email="socorro-dev@mozilla.com",
    license="MPL",
    url="https://github.com/mozilla-services/socorro",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MPL License",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    keywords=["socorro", "breakpad", "crash", "reporting", "minidump", "stacktrace"],
    packages=find_packages(),
    install_requires=[],  # use pip -r requirements.txt instead
    scripts=["socorro-cmd"],
    zip_safe=False,
    data_files=[
        ("socorro/siglists", glob.glob("socorro/signature/siglists/*.txt")),
        ("socorro/schemas", glob.glob("socorro/schemas/*.json")),
    ],
)
