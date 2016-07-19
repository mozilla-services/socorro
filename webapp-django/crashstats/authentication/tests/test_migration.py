import contextlib
import csv
import datetime
import os
import re
import tempfile

from nose.tools import ok_, eq_

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.utils.six import StringIO
from django.utils import timezone

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.authentication.migration import migrate_users

User = get_user_model()


@contextlib.contextmanager
def redirect_stdout(stream):
    import sys
    sys.stdout = stream
    yield
    sys.stdout = sys.__stdout__


class TestMigrateUsersCSV(DjangoTestCase):

    def test_basic_call(self):
        out = StringIO()
        tmp_csv_file = os.path.join(tempfile.gettempdir(), 'file.csv')
        with open(tmp_csv_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['alias', 'correct'])
            writer.writerow(['alias@example.com', 'flastname@example.com'])
        try:
            call_command('migrate-users-csv', tmp_csv_file, stdout=out)
            ok_(not out.getvalue())
        finally:
            os.remove(tmp_csv_file)

    def test_migrate_users(self):
        today = timezone.now()
        yesterday = today - datetime.timedelta(days=1)

        cool = Group.objects.create(name='Cool People')
        not_cool = Group.objects.create(name='Not So Cool')

        # create a user with "an alias email"
        alias = User.objects.create(username='a', email='Alias@example.com')
        # and give it some fancy permissions
        alias.is_staff = True
        alias.is_superuser = True
        alias.last_login = today
        alias.save()
        alias.groups.add(cool)
        alias.groups.add(not_cool)

        real = User.objects.create(username='r', email='Flastname@example.com')
        real.last_login = yesterday
        real.save()
        # just one group
        real.groups.add(not_cool)

        alias2 = User.objects.create(username='a2', email='Alias2@example.com')

        combos = (
            [alias.email.upper(), real.email.capitalize()],
            [alias2.email, 'corrected@example.com'],
            ['other@example.com', 'notfound@example.com'],
        )
        out = StringIO()
        with redirect_stdout(out):
            migrate_users(combos)

        # Check the stdout blather
        ok_(re.findall(
            'NEED TO MIGRATE Alias@example.com\s+TO Flastname@example.com',
            out.getvalue()
        ))
        ok_(re.findall(
            'NEED TO MIGRATE Alias2@example.com\s+TO corrected@example.com',
            out.getvalue()
        ))

        # Should still only be 3 users
        assert User.objects.all().count() == 3

        # It should have now "copied" all the good stuff of `alias`
        # over to `real`.
        alias = User.objects.get(id=alias.id)  # reload
        ok_(not alias.is_active)
        real = User.objects.get(id=real.id)
        ok_(real.is_staff)
        ok_(real.is_superuser)
        ok_(cool in real.groups.all())
        ok_(not_cool in real.groups.all())
        eq_(real.last_login, today)

        # And the `alias2` user should just simply have its email changed.
        ok_(not User.objects.filter(email__iexact='alias2@example.com'))
        ok_(User.objects.filter(email__iexact='corrected@example.com'))
