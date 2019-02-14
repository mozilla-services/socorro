# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import six

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.utils import timezone

from crashstats.tokens.models import Token


class TestAuditGroupsCommand(object):
    def test_no_users(self, db):
        buffer = six.StringIO()
        call_command('auditgroups', stdout=buffer)
        assert 'Removing:' not in buffer.getvalue()

    def test_inactive_user_is_removed(self, db):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now()
        bob.is_active = False
        bob.groups.add(hackers_group)
        bob.save()

        assert hackers_group.user_set.count() == 1

        buffer = six.StringIO()
        call_command('auditgroups', persist=True, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == []
        assert 'Removing: bob@mozilla.com (!is_active)' in buffer.getvalue()

        assert hackers_group.user_set.count() == 0

    def test_old_user_is_removed(self, db):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now() - datetime.timedelta(days=366)
        bob.groups.add(hackers_group)
        bob.save()

        buffer = six.StringIO()
        call_command('auditgroups', persist=True, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == []
        assert 'Removing: bob@mozilla.com (inactive 366d, no tokens)' in buffer.getvalue()

    def test_user_with_invalid_email_removed(self, db):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@example.com')
        bob.last_login = timezone.now()
        bob.groups.add(hackers_group)
        bob.save()

        buffer = six.StringIO()
        call_command('auditgroups', persist=True, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == []
        assert 'Removing: bob@example.com (invalid email domain)' in buffer.getvalue()

    def test_old_user_with_active_api_tokens_is_not_removed(self, db):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now() - datetime.timedelta(days=366)
        bob.groups.add(hackers_group)
        bob.save()

        token = Token.objects.create(user=bob)
        token.save()

        buffer = six.StringIO()
        call_command('auditgroups', persist=True, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == ['bob@mozilla.com']
        assert (
            'SKIP: bob@mozilla.com (inactive 366d, but has active tokens: 1)' in buffer.getvalue()
        )

    def test_active_user_is_not_removed(self, db):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now()
        bob.groups.add(hackers_group)
        bob.save()

        buffer = six.StringIO()
        call_command('auditgroups', persist=True, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == ['bob@mozilla.com']
        assert 'Removing:' not in buffer.getvalue()

    def test_persist_false(self, db):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now() - datetime.timedelta(days=366)
        bob.groups.add(hackers_group)
        bob.save()

        assert hackers_group.user_set.count() == 1

        buffer = six.StringIO()
        call_command('auditgroups', persist=False, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == ['bob@mozilla.com']
        assert 'Removing: bob@mozilla.com (inactive 366d, no tokens)' in buffer.getvalue()

        assert hackers_group.user_set.count() == 1
