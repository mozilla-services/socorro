# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.apps import AppConfig


class ManageConfig(AppConfig):
    name = "crashstats.manage"

    def ready(self):
        # Import our admin site code so it creates the admin site and
        # monkey-patches things and makes everything right as rain.
        from crashstats.manage import admin_site  # noqa
