# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from socorro import settings
from socorro.libclass import build_instance_from_settings


class Command(BaseCommand):
    help = "Delete expired Elasticsearch indices."

    def handle(self, **options):
        es = build_instance_from_settings(settings.CRASH_DESTINATIONS["elasticsearch"])
        indices = es.delete_expired_indices()
        if indices:
            self.stdout.write("Deleting expired crash report indices.")
            for index in indices:
                self.stdout.write("Deleting %s" % index)
        else:
            self.stdout.write("No expired indices to delete.")
