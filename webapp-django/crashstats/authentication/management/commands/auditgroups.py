# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Audit groups and removes inactive users.
"""

import datetime

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone


VALID_EMAIL_DOMAINS = ('mozilla.com', 'mozilla.org')


def delta_days(since_datetime):
    """Return the delta in days between now and since_datetime"""
    return (timezone.now() - since_datetime).days


class Command(BaseCommand):
    help = 'Audits Django groups and removes inactive users.'

    def add_arguments(self, parser):
        # FIXME(willkg): change this to default to False after we've tested
        # it.
        parser.add_argument(
            '--persist', action='store_true',
            help='persists recommended changes to db'
        )

    def audit_hackers_group(self, persist=False):
        # Figure out the cutoff date for inactivity
        cutoff = timezone.now() - datetime.timedelta(days=365)

        self.stdout.write('Using cutoff: %s' % cutoff)

        # Get all users in the "Hackers" group
        try:
            hackers_group = Group.objects.get(name='Hackers')
        except Group.DoesNotExist:
            self.stdout.write('"Hackers" group does not exist.')
            return

        # Go through the users and mark the ones for removal
        users_to_remove = []
        for user in hackers_group.user_set.all():
            if not user.is_active:
                users_to_remove.append((user, '!is_active'))
            elif not user.email.endswith(VALID_EMAIL_DOMAINS):
                users_to_remove.append((user, 'invalid email domain'))
            elif user.last_login and user.last_login < cutoff:
                days = delta_days(user.last_login)

                # This user is inactive. Check for active API tokens.
                active_tokens = [
                    token for token in user.token_set.all()
                    if not token.is_expired
                ]
                if not active_tokens:
                    users_to_remove.append((user, 'inactive %sd, no tokens' % days))
                else:
                    self.stdout.write(
                        'SKIP: %s (inactive %sd, but has active tokens: %s)' % (
                            user.email, days, len(active_tokens)
                        )
                    )

        # Log or remove the users that have been marked
        for user, reason in users_to_remove:
            self.stdout.write('Removing: %s (%s)' % (user.email, reason))
            if persist is True:
                hackers_group.user_set.remove(user)

        self.stdout.write('Total removed: %s' % len(users_to_remove))

    def handle(self, **options):
        persist = options['persist']
        if not persist:
            self.stdout.write('Dry run--this is what we think should happen.')
        self.audit_hackers_group(persist)
