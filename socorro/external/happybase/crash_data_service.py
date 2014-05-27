# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.crash_data_service_base import CrashDataBase

from configman import Namespace, class_converter


class CrashData(CrashDataBase):
    """
    Implement the /crash_data service with HBase.
    """
    required_config = Namespace()
    required_config.add_option(
        'crashstorage_class',
        default='socorro.external.happybase.crashstorage.HBaseCrashStorage',
        from_string_converter=class_converter,
        reference_value_from='resource.hb',
    )

