# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.apps import AppConfig
from django.conf import settings

import markus


class CrashstatsConfig(AppConfig):
    name = "crashstats.crashstats"

    def ready(self):
        # Import signals kicking off signal registration
        from crashstats.crashstats import signals  # noqa

        # Set up markus metrics
        markus.configure(backends=settings.MARKUS_BACKENDS)
