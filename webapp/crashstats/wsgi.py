# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crashstats.settings")

from django.core.wsgi import get_wsgi_application  # noqa

application = get_wsgi_application()
