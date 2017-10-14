import contextlib
from StringIO import StringIO

import mock
import pytest

from django.contrib.auth.models import User
from django.core.management.base import CommandError

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.authentication.management.commands import makesuperuser


@contextlib.contextmanager
def redirect_stdout(stream):
    import sys
    sys.stdout = stream
    yield
    sys.stdout = sys.__stdout__


@contextlib.contextmanager
def redirect_stderr(stream):
    import sys
    sys.stderr = stream
    yield
    sys.stderr = sys.__stderr__


class TestMakeSuperuserCommand(DjangoTestCase):

    def test_make_existing_user(self):
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        cmd = makesuperuser.Command()
        buffer = StringIO()
        with redirect_stdout(buffer):
            cmd.handle(emailaddress=['BOB@mozilla.com'])
        assert 'bob@mozilla.com is now a superuser' in buffer.getvalue()
        # reload
        assert User.objects.get(pk=bob.pk, is_superuser=True)

    def test_make_already_user(self):
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.is_superuser = True
        bob.save()
        cmd = makesuperuser.Command()
        buffer = StringIO()
        with redirect_stdout(buffer):
            cmd.handle(emailaddress=['BOB@mozilla.com'])
        assert 'bob@mozilla.com was already a superuser' in buffer.getvalue()
        # reload
        assert User.objects.get(pk=bob.pk, is_superuser=True)

    def test_make_two_user_superuser(self):
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.is_superuser = True  # already
        bob.save()
        otto = User.objects.create(username='otto', email='otto@mozilla.com')
        cmd = makesuperuser.Command()
        buffer = StringIO()
        with redirect_stdout(buffer):
            cmd.handle(emailaddress=['BOB@mozilla.com', 'oTTo@mozilla.com'])
        assert User.objects.get(pk=bob.pk, is_superuser=True)
        assert User.objects.get(pk=otto.pk, is_superuser=True)

    def test_nonexisting_user(self):
        cmd = makesuperuser.Command()
        buffer = StringIO()
        email = 'neverheardof@mozilla.com'
        with redirect_stdout(buffer):
            cmd.handle(emailaddress=[email])
        assert User.objects.get(email=email, is_superuser=True)
        assert '{} is now a superuser'.format(email) in buffer.getvalue()

    @mock.patch(
        'crashstats.authentication.management.commands.makesuperuser.'
        'get_input',
        return_value='BOB@mozilla.com '
    )
    def test_with_raw_input(self, mocked_raw_input):
        User.objects.create(username='bob', email='bob@mozilla.com')
        cmd = makesuperuser.Command()
        buffer = StringIO()
        with redirect_stdout(buffer):
            cmd.handle(emailaddress=[])
        # reload
        assert User.objects.get(email='bob@mozilla.com', is_superuser=True)

    @mock.patch(
        'crashstats.authentication.management.commands.makesuperuser.'
        'get_input',
        return_value='\n'
    )
    def test_with_raw_input_but_empty(self, mocked_raw_input):
        cmd = makesuperuser.Command()
        with pytest.raises(CommandError):
            cmd.handle(emailaddress=[])
