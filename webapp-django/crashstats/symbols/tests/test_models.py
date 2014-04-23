import shutil
import tempfile
import os

from nose.tools import ok_

from django.contrib.auth.models import User
from django.core.files import File

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.symbols import models
from .base import ZIP_FILE


class TestModels(DjangoTestCase):

    def setUp(self):
        super(TestModels, self).setUp()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(TestModels, self).tearDown()
        shutil.rmtree(self.tmp_dir)

    def test_create_symbols_upload(self):
        user = User.objects.create(username='user')
        assert os.path.isfile(ZIP_FILE), ZIP_FILE
        with self.settings(MEDIA_ROOT=self.tmp_dir):
            with open(ZIP_FILE, 'rb') as file_object:
                upload = models.SymbolsUpload.objects.create(
                    user=user,
                    file=File(file_object),
                    filename=os.path.basename(ZIP_FILE),
                    size=12345,
                    content='Content'
                )
        ok_(upload.file_exists)
        ok_(os.path.isdir(os.path.join(self.tmp_dir, 'symbols-uploads')))
        os.remove(upload.file.path)
        ok_(not upload.file_exists)
