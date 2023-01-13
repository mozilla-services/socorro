# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from crashstats.status.models import StatusMessage


def status_message(request):
    return {
        "status_messages": (
            StatusMessage.objects.filter(enabled=True).order_by("-created_at")
        )
    }
