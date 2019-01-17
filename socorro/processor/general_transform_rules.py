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
        # This is the CPU that the product was built for
        processed_crash['cpu_arch'] = glom(
            processed_crash, 'json_dump.system_info.cpu_arch', default=''
        )
        # NOTE(willkg): "cpu_name" is deprecated and we can remove it in July 2019
        processed_crash['cpu_name'] = glom(
            processed_crash, 'json_dump.system_info.cpu_arch', default=''
        )

        # This is the CPU info of the machine the product was running on
        processed_crash['cpu_info'] = glom(
            processed_crash, 'json_dump.system_info.cpu_info', default=''
        )
        processed_crash['cpu_count'] = glom(
            processed_crash, 'json_dump.system_info.cpu_count', default=0
        )


class OSInfoRule(Rule):
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        os_name = glom(processed_crash, 'json_dump.system_info.os', default='Unknown').strip()
        processed_crash['os_name'] = os_name

        os_ver = glom(processed_crash, 'json_dump.system_info.os_ver', default='').strip()
        processed_crash['os_version'] = os_ver
