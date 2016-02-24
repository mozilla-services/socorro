import datetime
import uuid

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Permission, Group
from django.utils import timezone
from django.dispatch import receiver


def get_future():
    delta = datetime.timedelta(days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS)
    return timezone.now() + delta


def make_key():
    return uuid.uuid4().hex


class TokenManager(models.Manager):

    def active(self):
        return self.get_queryset().filter(expires__gt=timezone.now())


class Token(models.Model):
    user = models.ForeignKey(User)
    key = models.CharField(max_length=32, default=make_key)
    expires = models.DateTimeField(default=get_future)
    permissions = models.ManyToManyField(Permission)
    notes = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)

    objects = TokenManager()

    def __repr__(self):
        return '<%s: %s...>' % (self.__class__.__name__, self.key[:12])

    @property
    def is_expired(self):
        return self.expires < timezone.now()


@receiver(models.signals.m2m_changed, sender=Group.permissions.through)
def drop_permissions_on_group_change(sender, instance, action, **kwargs):
    if action == 'post_remove':
        # A permission was removed from a group.
        # Every Token that had this permission needs to be re-evaluated
        # because, had the user created this token now, they might
        # no longer have access to that permission due to their
        # group memberships.
        permissions = Permission.objects.filter(id__in=kwargs['pk_set'])
        for permission in permissions:
            for token in Token.objects.filter(permissions=permission):
                user_permissions = Permission.objects.filter(
                    group__user=token.user
                )
                if permission not in user_permissions:
                    token.permissions.remove(permission)
