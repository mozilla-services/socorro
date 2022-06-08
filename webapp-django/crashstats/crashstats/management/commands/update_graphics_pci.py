# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Update GraphicsDevices information using data from https://pci-ids.ucw.cz/ .
"""

from django.core.management.base import BaseCommand

from crashstats.crashstats import utils
from crashstats.crashstats.models import GraphicsDevice
from socorro.lib.librequests import session_with_retries


PCI_IDS_URL = "https://pci-ids.ucw.cz/v2.2/pci.ids"


class Command(BaseCommand):
    help = "Update crashstats_graphicsdevice table using https://pci-ids.ucw.cz/"

    def add_arguments(self, parser):
        parser.add_argument("--debug", default=False, help="Print debugging output.")

    def handle(self, **options):
        debug_mode = options.get("debug")

        # Request file
        session = session_with_retries()

        resp = session.get(PCI_IDS_URL)

        # Let's raise an error if there's an error and let it alert us in Sentry for now
        resp.raise_for_status()

        # If we got the file successfully, then process it
        self.stdout.write(f"Fetch successful, {len(resp.text)} bytes...")
        devices = utils.pci_ids__parse_graphics_devices_iterable(
            resp.text.splitlines(), debug=debug_mode
        )

        total_created = 0
        total_updated = 0
        total_skipped = 0

        for item in devices:
            obj, created = GraphicsDevice.objects.get_or_create(
                vendor_hex=item["vendor_hex"], adapter_hex=item["adapter_hex"]
            )
            if (
                obj.vendor_name == item["vendor_name"]
                and obj.adapter_name == item["adapter_name"]
            ):
                total_skipped += 1
                continue

            obj.vendor_name = item["vendor_name"]
            obj.adapter_name = item["adapter_name"]
            obj.save()

            if created:
                total_created += 1
            else:
                total_updated += 1

        self.stdout.write(
            f"Done. "
            f"Created: {total_created}; "
            f"Updated: {total_updated}; "
            f"Skipped: {total_skipped}"
        )
