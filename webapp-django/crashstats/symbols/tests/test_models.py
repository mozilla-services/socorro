import os

from nose.tools import ok_

from django.contrib.auth.models import User

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.symbols import models
from .base import ZIP_FILE


class TestModels(DjangoTestCase):

    def test_create_symbols_upload(self):
        user = User.objects.create(username='user')
        upload = models.SymbolsUpload.objects.create(
            user=user,
            filename=os.path.basename(ZIP_FILE),
            size=12345,
            content='Content'
        )
        ok_(os.path.basename(ZIP_FILE) in repr(upload))
