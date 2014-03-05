import datetime
import hashlib
import os
import unicodedata

from django.db import models
from django.contrib.auth.models import User

from crashstats.base.utils import get_now


def uploader(instance, filename):
    if isinstance(filename, unicode):
        filename = (
            unicodedata
            .normalize('NFD', filename)
            .encode('ascii', 'ignore')
        )
    now = datetime.datetime.now()
    path = os.path.join(now.strftime('%Y'), now.strftime('%m'),
                        now.strftime('%d'))
    hashed_filename = (hashlib.md5(filename +
                       str(now.microsecond)).hexdigest())
    __, extension = os.path.splitext(filename)
    return os.path.join('symbols-uploads', path, hashed_filename + extension)


class SymbolsUpload(models.Model):
    user = models.ForeignKey(User)
    content = models.TextField()
    filename = models.CharField(max_length=100)
    file = models.FileField(null=True, upload_to=uploader)
    size = models.IntegerField()
    created = models.DateTimeField(default=get_now)

    def __repr__(self):
        return '<%s: %r...>' % (self.__class__.__name__, self.content[:100])

    @property
    def file_exists(self):
        return self.file and os.path.isfile(self.file.path)
