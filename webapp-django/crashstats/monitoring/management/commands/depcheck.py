# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Checks Python and JS dependencies for security updates.
"""

import json
import os
from collections import namedtuple
from os.path import dirname
from subprocess import PIPE, Popen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from socorro.lib import raven_client


VulnerabilityBase = namedtuple('Vulnerability', (
    'type',
    'dependency',
    'installed_version',
    'affected_versions',
    'description',
))


class Vulnerability(VulnerabilityBase):
    @property
    def key(self):
        return '[%s] %s' % (self.type, self.dependency)

    @property
    def summary(self):
        return 'Installed: %s; Affected: %s; %s' % (
            self.installed_version,
            self.affected_versions,
            self.description,
        )


class DependencySecurityCheckFailed(Exception):
    """Thrown when a security check cannot complete, such as network
    issues.

    """


class Command(BaseCommand):
    help = 'Check dependencies for security updates'

    def handle(self, **options):
        self.validate_options()

        vulnerabilities = self.get_python_vulnerabilities() + self.get_javascript_vulnerabilities()
        if vulnerabilities:
            try:
                dsn = settings.RAVEN_DSN
            except KeyError:
                dsn = None

            if dsn:
                self.alert_sentry(dsn, vulnerabilities)
            else:
                self.alert_log(vulnerabilities)

    def validate_options(self):
        # Validate file path options
        for option in ('NPM_PATH', 'SAFETY_PATH', 'PACKAGE_JSON_PATH'):
            value = getattr(settings, option)
            if not value:
                raise CommandError('Required option "%s" is empty' % option)
            elif not os.path.exists(value):
                raise CommandError(
                    'Option "%s" points to a nonexistant file (%s)' % (option, value)
                )
            elif not os.path.isfile(value):
                raise CommandError('Option "%s" does not point to a file (%s)' % (option, value))

    def alert_sentry(self, dsn, vulnerabilities):
        client = raven_client.get_client(dsn)
        client.context.activate()
        client.context.merge({
            'extra': {
                'data': {vuln.key: vuln.summary for vuln in vulnerabilities},
            },
        })
        client.captureMessage('Dependency security check failed')

    def alert_log(self, vulnerabilities):
        self.stdout.write('Vulnerabilities found in dependencies!')
        for vuln in vulnerabilities:
            self.stdout.write('%s: %s' % (vuln.key, vuln.summary))

    def get_python_vulnerabilities(self):
        """Check Python dependencies via Pyup's safety command.

        :returns list(Vulnerability):
        :raises DependencySecurityCheckFailed:

        """
        # Safety checks what's installed in the current virtualenv, so no need
        # for any paths.
        cmd = [settings.SAFETY_PATH, 'check', '--json']
        if getattr(settings, 'SAFETY_API_KEY', ''):
            cmd += ['--key', settings.SAFETY_API_KEY]

        process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, error_output = process.communicate()

        if process.returncode == 0:
            return []
        elif process.returncode == 255:
            try:
                results = json.loads(output)
                return [
                    Vulnerability(
                        type='python',
                        dependency=result[0],
                        installed_version=result[2],
                        affected_versions=result[1],
                        description=result[3],
                    ) for result in results
                ]
            except (ValueError, IndexError) as err:
                raise DependencySecurityCheckFailed(
                    'Could not parse pyup safety output',
                    err,
                    output,
                )

        raise DependencySecurityCheckFailed(error_output)

    def get_javascript_vulnerabilities(self):
        """Check JavaScript dependencies via the nsp command.

        :returns list(Vulnerability):
        :raises DependencySecurityCheckFailed:
        """
        process = Popen(
            [
                settings.NPM_PATH,
                'audit',
                '--json',
            ],
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            cwd=dirname(settings.PACKAGE_JSON_PATH),
        )
        output, error_output = process.communicate()
        if process.returncode == 0:
            return []
        elif process.returncode == 1:
            try:
                results = json.loads(output)
                return [
                    Vulnerability(
                        type='javascript',
                        dependency=result[1]['module_name'],
                        installed_version=result[1]['findings'][0]['version'],
                        affected_versions=result[1]['vulnerable_versions'],
                        description=result[1]['url'],
                    ) for result in results['advisories'].items()
                ]
            except (ValueError, KeyError) as err:
                raise DependencySecurityCheckFailed('Could not parse nsp output', err, output)

        raise DependencySecurityCheckFailed(error_output)
