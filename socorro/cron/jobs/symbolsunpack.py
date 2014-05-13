# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from configman import Namespace

from crontabber.base import BaseCronApp
from crontabber.mixins import with_subprocess

from socorro.lib.datetimeutil import utc_now


@with_subprocess
class SymbolsUnpackCronApp(BaseCronApp):
    app_name = 'symbols-unpack'
    app_description = 'Unpacks archives to go into the symbols store'

    required_config = Namespace()
    required_config.add_option(
        'source_directory',
        doc='Directory where the archive files are located',
        default='',
    )

    required_config.add_option(
        'destination_directory',
        doc='Directory where the archive files are unpacked to',
        default='',
    )

    def run(self):
        now = utc_now()

        walker = os.walk(self.config.source_directory, followlinks=True)
        for path, directories, files in walker:
            for filename in files:
                filepath = os.path.join(path, filename)
                if filename.lower().endswith('.tar.gz'):
                    destination = filename.replace('.tar.gz', '')
                else:
                    destination = os.path.splitext(filename)[0]
                destination = destination.replace(' ', '_')
                destination += '-' + now.strftime('%Y%m%d')

                destination_dir = self.config.destination_directory
                if not os.path.isdir(destination_dir):
                    raise IOError(destination_dir)

                if filename.lower().endswith('.zip'):
                    command = 'unzip -n "%s" -d "%s"' % (
                        filepath, destination_dir
                    )
                elif filename.lower().endswith('.tar'):
                    command = 'tar -xf "%s" -C "%s"' % (
                        filepath, destination_dir
                    )
                elif (
                    filename.lower().endswith('.tar.gz') or
                    filename.lower().endswith('.tgz')
                ):

                    command = 'tar -zxf "%s" -C "%s"' % (
                        filepath, destination_dir
                    )
                else:
                    self.config.logger.warning(
                        "Don't know how to unpack %s" % filepath
                    )
                    continue

                exit_code, stdout, stderr = self.run_process(command)
                if exit_code:
                    # something went wrong
                    raise ValueError(
                        'Unable to extract %s\n (out: %r)\n(error: %r)' % (
                            filepath, stdout, stderr
                        )
                    )
                else:
                    os.remove(filepath)

                    directory = path
                    while directory != self.config.source_directory:
                        if os.listdir(directory):
                            break
                        else:
                            # it's empty
                            os.rmdir(directory)
                        directory = os.path.normpath(
                            os.path.join(directory, '..')
                        )
