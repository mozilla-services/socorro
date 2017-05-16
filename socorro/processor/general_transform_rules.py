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

        system_info = processed_crash.json_dump.get('system_info')
        if system_info:
            processed_crash.cpu_name = system_info.get('cpu_arch', '')
            try:
                processed_crash.cpu_info = (
                    '%s | %s' % (
                        system_info['cpu_info'],
                        system_info['cpu_count']
                    )
                )
            except KeyError:
                # cpu_count is likely missing
                processed_crash.cpu_info = system_info.get('cpu_info', '')

        return True


class OSInfoRule(Rule):
    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.os_name = ''
        processed_crash.os_version = ''

        system_info = processed_crash.json_dump.get('system_info')
        if system_info:
            processed_crash.os_name = system_info.get('os', '').strip()
            processed_crash.os_version = system_info.get('os_ver', '').strip()

        return True
