# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Audit groups and removes inactive users.
"""

import datetime

from django.contrib.auth.models import Group, User
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from crashstats.authentication.models import PolicyException


VALID_EMAIL_DOMAINS = ("mozilla.com", "mozilla.org")


def get_or_create_auditgroups_user():
    try:
        return User.objects.get(username="auditgroups")
    except User.DoesNotExist:
        return User.objects.create_user(
            username="auditgroups",
            email="auditgroups@example.com",
            first_name="SYSTEMUSER",
            last_name="DONOTDELETE",
            is_active=False,
        )


def delta_days(since_datetime):
    """Return the delta in days between now and since_datetime"""
    return (timezone.now() - since_datetime).days


class Command(BaseCommand):
    help = "Audits Django groups and removes inactive users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Whether or not to do a dry run."
        )

    def is_employee_or_exception(self, user):
        # If this user has a policy exception, then they're allowed
        if PolicyException.objects.filter(user=user).exists():
            return True

        if user.email.endswith(VALID_EMAIL_DOMAINS):
            return True

        return False

    def audit_hackers_group(self, dryrun=True):
        # Figure out the cutoff date for inactivity
        cutoff = timezone.now() - datetime.timedelta(days=365)

        self.stdout.write("Using cutoff: %s" % cutoff)

        # Get all users in the "Hackers" group
        try:
            hackers_group = Group.objects.get(name="Hackers")
        except Group.DoesNotExist:
            self.stdout.write('"Hackers" group does not exist.')
            return

        # Go through the users and mark the ones for removal
        users_to_remove = []
        for user in hackers_group.user_set.all():
            if not user.is_active:
                users_to_remove.append((user, "!is_active"))

            elif not self.is_employee_or_exception(user):
                users_to_remove.append((user, "not employee or exception"))

            elif user.last_login and user.last_login < cutoff:
                days = delta_days(user.last_login)

                # This user is inactive. Check for active API tokens.
                active_tokens = [
                    token for token in user.token_set.all() if not token.is_expired
                ]
                if not active_tokens:
                    users_to_remove.append((user, "inactive %sd, no tokens" % days))
                else:
                    self.stdout.write(
                        "SKIP: %s (inactive %sd, but has active tokens: %s)"
                        % (user.email, days, len(active_tokens))
                    )

        auditgroups_user = get_or_create_auditgroups_user()

        # Log or remove the users that have been marked
        for user, reason in users_to_remove:
            self.stdout.write("Removing: %s (%s)" % (user.email, reason))
            if dryrun is False:
                hackers_group.user_set.remove(user)

                # Toss a LogEntry in so we can keep track of when people get
                # de-granted and what did it
                LogEntry.objects.log_action(
                    user_id=auditgroups_user.id,
                    content_type_id=ContentType.objects.get_for_model(User).pk,
                    object_id=user.pk,
                    object_repr=user.email,
                    action_flag=CHANGE,
                    change_message="Removed %s from hackers--%s."
                    % (user.email, reason),
                )

        self.stdout.write("Total removed: %s" % len(users_to_remove))

    def handle(self, **options):
        dryrun = options["dry_run"]
        if dryrun:
            self.stdout.write("Dry run--this is what we think should happen.")
        self.audit_hackers_group(dryrun=dryrun)
