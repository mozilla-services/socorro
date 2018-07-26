import datetime
from StringIO import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.utils import timezone

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.tokens.models import Token


class TestAuditGroupsCommand(DjangoTestCase):
    def test_no_users(self):
        buffer = StringIO()
        call_command('auditgroups', stdout=buffer)
        assert 'Removing:' not in buffer.getvalue()

    def test_inactive_user_is_removed(self):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now()
        bob.is_active = False
        bob.groups.add(hackers_group)
        bob.save()

        buffer = StringIO()
        call_command('auditgroups', dryrun=False, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == []
        assert 'Removing: bob@mozilla.com (!is_active)' in buffer.getvalue()

    def test_old_user_is_removed(self):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now() - datetime.timedelta(days=366)
        bob.groups.add(hackers_group)
        bob.save()

        buffer = StringIO()
        call_command('auditgroups', dryrun=False, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == []
        assert 'Removing: bob@mozilla.com (inactive since cutoff, no tokens)' in buffer.getvalue()

    def test_user_with_invalid_email_removed(self):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@example.com')
        bob.last_login = timezone.now()
        bob.groups.add(hackers_group)
        bob.save()

        buffer = StringIO()
        call_command('auditgroups', dryrun=False, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == []
        assert 'Removing: bob@example.com (invalid email)' in buffer.getvalue()

    def test_old_user_with_active_api_tokens_is_not_removed(self):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now() - datetime.timedelta(days=366)
        bob.groups.add(hackers_group)
        bob.save()

        token = Token.objects.create(user=bob)
        token.save()

        buffer = StringIO()
        call_command('auditgroups', dryrun=False, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == ['bob@mozilla.com']
        assert 'SKIP: bob@mozilla.com (inactive, but has active tokens: 1)' in buffer.getvalue()

    def test_active_user_is_not_removed(self):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now()
        bob.groups.add(hackers_group)
        bob.save()

        buffer = StringIO()
        call_command('auditgroups', dryrun=False, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == ['bob@mozilla.com']
        assert 'Removing:' not in buffer.getvalue()

    def test_dryrun(self):
        hackers_group = Group.objects.get(name='Hackers')

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.last_login = timezone.now() - datetime.timedelta(days=366)
        bob.groups.add(hackers_group)
        bob.save()

        buffer = StringIO()
        call_command('auditgroups', dryrun=True, stdout=buffer)
        assert [u.email for u in hackers_group.user_set.all()] == ['bob@mozilla.com']
        assert 'Removing: bob@mozilla.com (inactive since cutoff, no tokens)' in buffer.getvalue()
