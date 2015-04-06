from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SymbolsUpload(models.Model):
    user = models.ForeignKey(User)
    content = models.TextField()
    filename = models.CharField(max_length=100)
    size = models.IntegerField()
    created = models.DateTimeField(default=timezone.now)
    content_type = models.TextField(null=True)

    def __repr__(self):
        return '<%s: %s (%d)...>' % (
            self.__class__.__name__,
            self.filename,
            self.size
        )
