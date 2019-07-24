# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Create a user.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a user."

    def add_arguments(self, parser):
        parser.add_argument("username", help="account username")
        parser.add_argument("password", help="account password")
        parser.add_argument("email", help="account email address")

    def handle(self, **options):
        username = options["username"]
        password = options["password"]
        email = options["email"]

        if User.objects.filter(username=username).exists():
            self.stdout.write("User {} already exists.".format(username))
            return

        user = User.objects.create(username=username, email=email)
        user.set_password(password)
        user.save()
        self.stdout.write("User {} created.".format(username))
