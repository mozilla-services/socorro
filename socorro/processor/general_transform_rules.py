# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from glom import glom

from socorro.processor.rules.base import Rule


class IdentifierRule(Rule):
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        if 'uuid' in raw_crash:
            processed_crash['crash_id'] = raw_crash['uuid']
            processed_crash['uuid'] = raw_crash['uuid']


class CPUInfoRule(Rule):
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        cpu_name = ''
        cpu_info = ''

        system_info = processed_crash.get('json_dump', {}).get('system_info')
        if system_info:
            cpu_name = system_info.get('cpu_arch', '')

            if 'cpu_info' in system_info and 'cpu_count' in system_info:
                cpu_info = (
                    '%s | %s' % (
                        system_info['cpu_info'],
                        system_info['cpu_count']
                    )
                )
            else:
                cpu_info = system_info.get('cpu_info', '')

        processed_crash['cpu_name'] = cpu_name
        processed_crash['cpu_info'] = cpu_info


class OSInfoRule(Rule):
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        os_name = glom(processed_crash, 'json_dump.system_info.os', default='Unknown').strip()
        processed_crash['os_name'] = os_name

        os_ver = glom(processed_crash, 'json_dump.system_info.os_ver', default='').strip()
        processed_crash['os_version'] = os_ver
