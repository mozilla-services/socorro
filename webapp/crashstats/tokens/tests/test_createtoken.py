# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import StringIO

import pytest

from django.core.management import call_command
from django.core.management.base import CommandError

from crashstats.tokens.models import make_key, Token


@pytest.mark.django_db
def test_createtoken_no_key_command():
    assert Token.objects.all().count() == 0
    stdout = StringIO()
    call_command("makesuperuser", "foo@example.com", stdout=stdout)
    stdout = StringIO()
    call_command("createtoken", "foo@example.com", stdout=stdout)

    assert Token.objects.all().count() == 1


@pytest.mark.django_db
def test_createtoken_with_key_command():
    assert Token.objects.all().count() == 0
    stdout = StringIO()
    call_command("makesuperuser", "foo@example.com", stdout=stdout)
    stdout = StringIO()
    token_key = make_key()
    call_command("createtoken", "foo@example.com", token_key, stdout=stdout)

    assert Token.objects.filter(key=token_key).count() == 1


@pytest.mark.django_db
def test_createtoken_command_no_user():
    with pytest.raises(CommandError):
        stdout = StringIO()
        call_command("createtoken", "foo@example.com", stdout=stdout)
