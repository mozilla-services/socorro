# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand, CommandError

from crashstats.tokens.models import make_key, Token


class Command(BaseCommand):
    help = "Create an API token."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("token_key", default=None, nargs="?")
        parser.add_argument(
            "--try-upload",
            action="store_true",
            help="If true, create the token with Upload Try Symbols",
        )

    def handle(self, *args, **options):
        email = options["email"]

        token_key = options["token_key"]
        if not token_key:
            token_key = make_key()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise CommandError(f"Account {email!r} does not exist.") from None

        if Token.objects.filter(user=user, key=token_key).exists():
            raise CommandError(f"Token with key {token_key!r} already exists")

        # Add permissions to token that user has
        permissions_to_add = [
            "view_pii",
            "view_rawdump",
            "reprocess_crashes",
        ]
        permissions = [
            Permission.objects.get(codename=permission)
            for permission in permissions_to_add
            if user.has_perm(permission)
        ]

        token = Token.objects.create(
            user=user,
            key=token_key,
        )
        self.stdout.write(self.style.SUCCESS(f"{token_key} created"))
        for permission in permissions:
            token.permissions.add(permission)
            self.stdout.write(self.style.SUCCESS(f"{permission} added"))
