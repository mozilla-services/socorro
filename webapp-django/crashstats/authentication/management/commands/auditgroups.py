"""
Audit groups and removes inactive users.
"""

from __future__ import print_function

import datetime

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone


VALID_EMAIL_DOMAINS = ('mozilla.com', 'mozilla.org')


class Command(BaseCommand):
    help = 'Audits Django groups and removes inactive users.'

    def add_arguments(self, parser):
        # FIXME(willkg): change this to default to False after we've tested
        # it.
        parser.add_argument(
            '--dryrun', type=bool, default=True,
            help='enables dry run which will not persist changes to db'
        )

    def audit_hackers_group(self, dryrun):
        # Figure out the cutoff date for inactivity
        cutoff = timezone.now() - datetime.timedelta(days=365)

        self.stdout.write('Using cutoff: {}'.format(cutoff))

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
                users_to_remove.append((user, 'invalid email'))
            elif user.last_login and user.last_login < cutoff:
                # This user is inactive. Check for active API tokens.
                active_tokens = [
                    token for token in user.token_set.all()
                    if not token.is_expired
                ]
                if not active_tokens:
                    users_to_remove.append((user, 'inactive since cutoff, no tokens'))
                else:
                    self.stdout.write(
                        'SKIP: {} (inactive, but has active tokens: {})'.format(
                            user.email, len(active_tokens)
                        )
                    )

        # Log or remove the users that have been marked
        for user, reason in users_to_remove:
            self.stdout.write('Removing: {} ({})'.format(user.email, reason))
            if not dryrun:
                hackers_group.user_set.remove(user)

    def handle(self, **options):
        dryrun = options['dryrun']

        self.audit_hackers_group(dryrun)
