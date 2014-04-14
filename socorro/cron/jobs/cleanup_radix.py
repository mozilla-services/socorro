# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace
from configman.converters import classes_in_namespaces_converter
from configman.dotdict import DotDict

from socorro.cron.base import BaseCronApp

from socorro.lib.datetimeutil import utc_now

import os
import shutil


class RadixCleanupCronApp(BaseCronApp):
    app_name = 'cleanup_radix'
    app_description = 'Cleans up dead radix directories'

    required_config = Namespace()
    required_config.add_option(
      'dated_storage_classes',
      doc='a comma delimited list of storage classes',
      default='',
      from_string_converter=classes_in_namespaces_converter(
          template_for_namespace='storage%d',
          name_of_class_option='crashstorage_class',
          instantiate_classes=False,  # we instantiate manually for thread
                                      # safety
      )
    )

    def __init__(self, config, *args, **kwargs):
        super(RadixCleanupCronApp, self).__init__(config, *args, **kwargs)
        self.storage_namespaces = \
          config.dated_storage_classes.subordinate_namespace_names
        self.stores = DotDict()
        for a_namespace in self.storage_namespaces:
            self.stores[a_namespace] = \
              config[a_namespace].crashstorage_class(config[a_namespace])

    def run(self):
        today = utc_now().strftime("%Y%m%d")

        for storage in self.stores.values():
            for date in os.listdir(storage.config.fs_root):
                if date >= today:
                    continue  # don't process today's crashes or any crashes
                              # from the future

                if os.listdir(os.sep.join([storage.config.fs_root, date,
                                           storage.config.date_branch_base])):
                    self.config.logger.error("Could not delete crashes for "
                                             "date %s: branch isn't empty",
                                             date)
                    continue  # if the date branch isn't empty, then it's not
                              # safe to nuke

                shutil.rmtree(os.sep.join([storage.config.fs_root, date]))
