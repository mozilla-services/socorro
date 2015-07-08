from nose.tools import ok_

from crashstats.symbols import utils
from crashstats.base.tests.testbase import TestCase

from .base import (
    ZIP_FILE,
    TAR_FILE,
    TGZ_FILE,
    TARGZ_FILE
)


class TestUtils(TestCase):

    def test_preview_zip(self):
        with open(ZIP_FILE) as f:
            result = utils.preview_archive_content(f, 'foo.zip')
            # the sample.zip file contains...
            ok_('south-africa-flag.jpeg' in result)
            # and it's 69183 bytes
            ok_('69183' in result)

    def test_preview_tar(self):
        with open(TAR_FILE) as f:
            result = utils.preview_archive_content(f, 'foo.tar')
            # the sample.tar file contains...
            ok_('south-africa-flag.jpeg' in result)
            # and it's 69183 bytes
            ok_('69183' in result)

    def test_preview_tgz(self):
        with open(TGZ_FILE) as f:
            result = utils.preview_archive_content(f, 'foo.tgz')
            # the sample.tgz file contains...
            ok_('south-africa-flag.jpeg' in result)
            # and it's 69183 bytes
            ok_('69183' in result)

    def test_preview_targz(self):
        with open(TARGZ_FILE) as f:
            result = utils.preview_archive_content(f, 'foo.tar.gz')
            # the sample.tar.gz file contains...
            ok_('south-africa-flag.jpeg' in result)
            # and it's 69183 bytes
            ok_('69183' in result)
