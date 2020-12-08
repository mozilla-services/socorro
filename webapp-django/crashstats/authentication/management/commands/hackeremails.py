# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Print email addresses of all users who are in the hacker group.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from crashstats.authentication.models import PolicyException


VALID_EMAIL_DOMAINS = ("mozilla.com", "mozilla.org")


class Command(BaseCommand):
    help = "Print email addresses of users in hacker group."

    def is_employee_or_exception(self, user):
        # If this user has a policy exception, then they're allowed
        if PolicyException.objects.filter(user=user).exists():
            return True

        if user.email.endswith(VALID_EMAIL_DOMAINS):
            return True

        return False

    def handle(self, **options):
        # Get all users in the "Hackers" group
        try:
            hackers_group = Group.objects.get(name="Hackers")
        except Group.DoesNotExist:
            self.stdout.write('"Hackers" group does not exist.')
            return

        # Go through users in the group and print out email address
        email_addresses = []
        for user in hackers_group.user_set.all():
            if not user.is_active or not self.is_employee_or_exception(user):
                continue

            email_addresses.append(user.email)

        if email_addresses:
            self.stdout.write("Users in Hackers group:")

            for email_address in email_addresses:
                self.stdout.write(email_address)
        else:
            self.stdout.write("No users.")
