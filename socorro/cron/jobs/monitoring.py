# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import os
from collections import namedtuple
from os.path import dirname
from subprocess import PIPE, Popen

from configman import Namespace
from configman.config_exceptions import OptionError
from crontabber.base import BaseCronApp

from socorro.lib import raven_client


PROJECT_ROOT = dirname(dirname(dirname(dirname(__file__))))


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


class DependencySecurityCheckCronApp(BaseCronApp):
    """Configuration values used by this app:

    crontabber.class-DependencySecurityCheckCronApp.nsp_path
        Path to the nsp binary for checking Node dependencies.
    crontabber.class-DependencySecurityCheckCronApp.safety_path
        Path to the PyUp Safety binary for checking Python dependencies.
    secrets.sentry.dsn
        If specified, vulnerabilities will be reported to Sentry instead
        of logged to the console.

    """
    app_name = 'dependency-security-check'
    app_description = (
        'Runs third-party tools that check for known security vulnerabilites in Socorro\'s '
        'dependencies.'
    )
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'nsp_path',
        doc='Path to the nsp binary',
    )
    required_config.add_option(
        'safety_path',
        doc='Path to the PyUp safety binary',
    )

    def run(self):
        self.validate_options()

        vulnerabilities = self.get_python_vulnerabilities() + self.get_javascript_vulnerabilities()
        if vulnerabilities:
            try:
                dsn = self.config.sentry.dsn
            except KeyError:
                dsn = None

            if dsn:
                self.alert_sentry(dsn, vulnerabilities)
            else:
                self.alert_log(vulnerabilities)

    def validate_options(self):
        # Validate binary path options
        for option in ('nsp_path', 'safety_path'):
            value = self.config.get(option)
            if not value:
                raise OptionError('Required option "%s" is empty' % option)
            elif not os.path.exists(value):
                raise OptionError('Option "%s" points to a nonexistant file (%s)' % (option, value))
            elif not os.path.isfile(value):
                raise OptionError('Option "%s" does not point to a file (%s)' % (option, value))

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
        self.config.logger.error('Vulnerabilities found in dependencies!')
        for vuln in vulnerabilities:
            self.config.logger.error('%s: %s' % (vuln.key, vuln.summary))

    def get_python_vulnerabilities(self):
        """Check Python dependencies via Pyup's safety command.

        :returns list(Vulnerability):
        :raises DependencySecurityCheckFailed:
        """
        # Safety checks what's installed in the current virtualenv, so no need
        # for any paths.
        process = Popen(
            [self.config.safety_path, 'check', '--json'],
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )
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
                self.config.nsp_path,
                'check',
                '--reporter=json',
            ],
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            cwd=os.path.join(PROJECT_ROOT, 'webapp-django'),
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
                        dependency=result['module'],
                        installed_version=result['version'],
                        affected_versions=result['vulnerable_versions'],
                        description=result['advisory'],
                    ) for result in results
                ]
            except (ValueError, KeyError) as err:
                raise DependencySecurityCheckFailed('Could not parse nsp output', err, output)

        raise DependencySecurityCheckFailed(error_output)
