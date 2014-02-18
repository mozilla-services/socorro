import datetime
import uuid

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.utils.timezone import utc


def get_now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)


def get_future():
    delta = datetime.timedelta(days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS)
    return get_now() + delta


def make_key():
    return uuid.uuid4().hex


class TokenManager(models.Manager):

    def active(self):
        return self.get_query_set().filter(expires__gt=get_now())


class Token(models.Model):
    user = models.ForeignKey(User)
    key = models.CharField(max_length=32, default=make_key)
    expires = models.DateTimeField(default=get_future)
    permissions = models.ManyToManyField(Permission)
    notes = models.TextField(blank=True)
    created = models.DateTimeField(default=get_now)

    objects = TokenManager()

    def __repr__(self):
        return '<%s: %s...>' % (self.__class__.__name__, self.key[:12])
