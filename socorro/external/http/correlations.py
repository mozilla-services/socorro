# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os
import re
import stat
import tempfile
import time

import requests

from socorro.lib import external_common


class DownloadError(Exception):
    pass


def file_age(f):
    return int(time.time() - os.stat(f)[stat.ST_MTIME])


COUNT_REGEX = re.compile('\((\d+) crashes\)')
SIGNATURE_LINE_START_REGEX = re.compile('\s{2}\w')


class Correlations(object):

    def __init__(self, config):
        self.config = config

    def get(self, **kwargs):
        filters = [
            ('report_type', None, 'str'),
            ('product', None, 'str'),
            ('version', None, 'str'),
            ('platform', None, 'str'),
            ('signature', None, 'str'),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        content = self._get_content(params)

        data = self._parse_content(
            content,
            params['platform'],
            params['signature']
        )
        reason, count, load = data
        return {
            'reason': reason,
            'count': count,
            'load': '\n'.join(load),
        }

    def _get_content(self, params):
        if 'http' in self.config and 'correlations' in self.config.http:
            # new middleware!
            base_url = self.config.http.correlations.base_url
            save_download = self.config.http.correlations.save_download
            save_seconds = int(self.config.http.correlations.save_seconds)
            save_root = self.config.http.correlations.save_root
        else:
            # old middleware where nesting (aka namespace) was not possible
            base_url = self.config.correlations_base_url
            save_download = self.config.correlations_save_download
            save_seconds = int(self.config.correlations_save_seconds)
            save_root = self.config.correlations_save_root

        date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        url_start = base_url + (
            '%(date)s/%(date)s_%(product)s_%(version)s-%(report_type)s'
            % dict(params, date=date.strftime('%Y%m%d'))
        )
        if not save_root:
            save_root = tempfile.gettempdir()
        save_dir = os.path.join(save_root, date.strftime('%Y%m%d'))
        if not os.path.isdir(save_dir):
            os.mkdir(save_dir)

        tmp_filepath = os.path.join(
            save_dir,
            '%s.txt' % url_start.split('/')[-1]
        )

        if (
            save_download and
            os.path.isfile(tmp_filepath) and
            file_age(tmp_filepath) < save_seconds
        ):
            content = open(tmp_filepath).read()
        else:
            content = self._download(url_start)
            if save_download:
                with open(tmp_filepath, 'w') as f:
                    f.write(content)
        return content

    @staticmethod
    def _download(url_start):
        response = requests.get(url_start + '.txt', verify=False)
        if response.status_code == 200:
            return response.content
        else:
            response = requests.get(url_start + '.txt.gz', verify=False)
            if response.status_code == 200:
                return response.content
            else:
                raise DownloadError(url_start + '(.txt|.txt.gz)')

    @staticmethod
    def _parse_content(content, platform, signature):

        on = False
        reason = count = None
        signature_found = False
        load = []
        this_platform = None
        for line in content.splitlines():
            if line and not line.startswith(' '):
                # change of platform
                this_platform = line
                if this_platform == platform:
                    on = True
                elif on:
                    # was on
                    break
            elif on:
                try:
                    this_signature = line.split('|')[-2].strip()
                    if this_signature == signature:
                        if signature_found:
                            break
                        signature_found = True
                        rest = line.split('|')[-1]
                        reason = rest.split('(')[0].strip()
                        count = int(COUNT_REGEX.findall(rest)[0])
                        continue
                except IndexError:
                    pass
                if signature_found:
                    if not line.strip():
                        break
                    else:
                        load.append(line.strip())

        return reason, count, load


class CorrelationSignatures(Correlations):

    def __init__(self, config):
        self.config = config

    def get(self, **kwargs):
        filters = [
            ('report_type', None, 'str'),
            ('product', None, 'str'),
            ('version', None, 'str'),
            ('platforms', None, 'list'),
        ]

        params = external_common.parse_arguments(filters, kwargs)
        content = self._get_content(params)
        signatures = self._parse_signatures(content, params['platforms'])

        return {
            'hits': signatures,
            'total': len(signatures),
        }

    @staticmethod
    def _parse_signatures(content, platforms):
        """return a list of signatures that these platforms mention"""
        signatures = []

        on = False
        for line in content.splitlines():
            if line and not line.startswith(' '):
                # change of platform
                if line in platforms:
                    on = True
                else:
                    on = False
            elif on:
                # if starts with exactly two spaces it contains the signature
                if SIGNATURE_LINE_START_REGEX.match(line):
                    this_signature = line.split('|')[-2].strip()
                    signatures.append(this_signature)

        return signatures
