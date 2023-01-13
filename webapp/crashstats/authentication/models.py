# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import models
from django.utils import timezone


class PolicyException(models.Model):
    """Exception to the must be a Mozilla employee.

    This is a table of users who have been granted an exception to the policy
    rule that requires them to be a Mozilla employee in order to have access to
    PII.

    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="This user is excepted from the Mozilla-employees-only policy.",
    )
    comment = models.TextField(help_text="Explanation for this exception.")
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "PolicyException <%d, %s>" % (self.id, self.user.email)
