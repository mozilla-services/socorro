import datetime

from nose.tools import eq_, ok_

from django.utils.timezone import utc
from django.contrib.auth.models import User
from django.conf import settings

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.tokens import models


class TestModels(DjangoTestCase):

    def test_create_token(self):
        bob = User.objects.create(username='bob')
        token = models.Token.objects.create(
            user=bob,
            notes='Some notes'
        )
        eq_(len(token.key), 32)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        future = now + datetime.timedelta(
            days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS
        )
        eq_(
            token.expires.strftime('%Y%m%d%H%M'),
            future.strftime('%Y%m%d%H%M')
        )

        # using __repr__ shouldn't reveal the key
        ok_(token.key not in repr(token))

    def test_token_manager(self):
        bob = User.objects.create(username='bob')
        models.Token.objects.create(
            user=bob,
            notes='Second one'
        )

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        models.Token.objects.create(
            user=bob,
            notes='First one',
            expires=now
        )
        eq_(models.Token.objects.all().count(), 2)
        eq_(models.Token.objects.active().count(), 1)

    def test_is_expired(self):
        bob = User.objects.create(username='bob')
        token = models.Token.objects.create(
            user=bob,
            notes='Some notes'
        )
        ok_(not token.is_expired)
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        yesterday = now - datetime.timedelta(days=1)
        token.expires = yesterday
        token.save()
        ok_(token.is_expired)
