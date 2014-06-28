import contextlib
from StringIO import StringIO

from nose.tools import ok_, assert_raises
import mock

from django.contrib.auth.models import User
from django.core.management.base import CommandError

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.auth.management.commands import makesuperuser


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
            cmd.handle('BOB@mozilla.com')
        ok_('bob@mozilla.com is now a superuser' in buffer.getvalue())
        # reload
        ok_(User.objects.get(pk=bob.pk, is_superuser=True))

    def test_make_already_user(self):
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.is_superuser = True
        bob.save()
        cmd = makesuperuser.Command()
        buffer = StringIO()
        with redirect_stdout(buffer):
            cmd.handle('BOB@mozilla.com')
        ok_('bob@mozilla.com was already a superuser' in buffer.getvalue())
        # reload
        ok_(User.objects.get(pk=bob.pk, is_superuser=True))

    def test_make_two_user_superuser(self):
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        bob.is_superuser = True  # already
        bob.save()
        otto = User.objects.create(username='otto', email='otto@mozilla.com')
        cmd = makesuperuser.Command()
        buffer = StringIO()
        with redirect_stdout(buffer):
            cmd.handle('BOB@mozilla.com oTTo@mozilla.com')
        ok_(User.objects.get(pk=bob.pk, is_superuser=True))
        ok_(User.objects.get(pk=otto.pk, is_superuser=True))

    def test_nonexisting_user(self):
        cmd = makesuperuser.Command()
        buffer = StringIO()
        with redirect_stderr(buffer):
            cmd.handle('neverheardof@mozilla.com')
        ok_(
            'No user with that email neverheardof@mozilla.com'
            in buffer.getvalue()
        )

    @mock.patch('crashstats.auth.management.commands.makesuperuser.get_input',
                return_value='BOB@mozilla.com ')
    def test_with_raw_input(self, mocked_raw_input):
        User.objects.create(username='bob', email='bob@mozilla.com')
        cmd = makesuperuser.Command()
        buffer = StringIO()
        with redirect_stdout(buffer):
            cmd.handle()
        # reload
        ok_(User.objects.get(email='bob@mozilla.com', is_superuser=True))

    @mock.patch('crashstats.auth.management.commands.makesuperuser.get_input',
                return_value='\n')
    def test_with_raw_input_but_empty(self, mocked_raw_input):
        cmd = makesuperuser.Command()
        assert_raises(
            CommandError,
            cmd.handle
        )
