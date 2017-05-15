# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.lib.transform_rules import Rule


class IdentifierRule(Rule):
    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.crash_id = raw_crash.uuid
        processed_crash.uuid = raw_crash.uuid

        return True


class CPUInfoRule(Rule):
    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.cpu_info = ''
        processed_crash.cpu_name = ''
        try:
            processed_crash.cpu_info = (
                '%s | %s' % (
                    processed_crash.json_dump['system_info']['cpu_info'],
                    processed_crash.json_dump['system_info']['cpu_count']
                )
            )
        except KeyError:
            # cpu_count is likely missing
            processed_crash.cpu_info = (
                processed_crash.json_dump['system_info']['cpu_info']
            )
        processed_crash.cpu_name = (
            processed_crash.json_dump['system_info']['cpu_arch']
        )

        return True


class OSInfoRule(Rule):
    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.os_name = ''
        processed_crash.os_version = ''
        processed_crash.os_name = (
            processed_crash.json_dump['system_info']['os'].strip()
        )
        processed_crash.os_version = (
            processed_crash.json_dump['system_info']['os_ver'].strip()
        )

        return True
