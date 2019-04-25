# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os

import pytest
from unittest import mock

from django.conf import settings
from django.core.management import CommandError
from django.test import override_settings

from crashstats.monitoring.management.commands.depcheck import (
    Command,
    DependencySecurityCheckFailed,
    Vulnerability,
)


@pytest.fixture
def mock_popen():
    popen_patch = mock.patch('crashstats.monitoring.management.commands.depcheck.Popen')
    popen = popen_patch.start()

    def _mock_popen(return_code, output='', error_output=''):
        process = popen.return_value
        process.returncode = return_code
        process.communicate.return_value = (output, error_output)
        return popen

    yield _mock_popen

    popen_patch.stop()


# Mocking Popen for multiple calls in a row is kinda hairy, so instead
# we're testing the separate get_*_vulnerabilities methods and then
# mocking them to test the main command.
class TestDepCheckCommand:
    def test_get_python_vulnerabilities_none(self, mock_popen):
        popen = mock_popen(0)

        assert Command().get_python_vulnerabilities() == []
        assert popen.call_args[0][0] == [settings.SAFETY_PATH, 'check', '--json']

    def test_get_python_vulnerabilities_with_key(self, mock_popen):
        key = 'fake-api-key'
        with override_settings(SAFETY_API_KEY=key):
            cmd = Command()
            popen = mock_popen(0)

            assert cmd.get_python_vulnerabilities() == []
            assert popen.call_args[0][0] == [
                settings.SAFETY_PATH,
                'check',
                '--json',
                '--key',
                key,
            ]

    def test_get_python_vulnerabilities_failure(self, mock_popen):
        """Handle failures like being unable to connect to the network."""
        cmd = Command()
        error_output = 'pretend-im-a-traceback'
        mock_popen(1, error_output='pretend-im-a-traceback')

        with pytest.raises(DependencySecurityCheckFailed) as err:
            cmd.get_python_vulnerabilities()
        assert err.value.args[0] == error_output

    def test_get_python_vulnerabilities_found(self, mock_popen):
        cmd = Command()

        # See https://github.com/pyupio/safety#--json for an example
        # of safety's JSON output
        output = json.dumps([
            [
                'mylibrary',  # Dependency name
                '<1.0.0',  # Affected version
                '0.9.0',  # Installed version
                'This is an error',  # Vulnerability summary
                '654',  # Advisory ID
            ],
            [
                'otherlib',
                '<2.0.0',
                '1.4.0',
                'This is also an error',
                '123',
            ],
        ])
        mock_popen(255, output=output)

        assert set(cmd.get_python_vulnerabilities()) == set([
            Vulnerability(
                type='python',
                dependency='mylibrary',
                installed_version='0.9.0',
                affected_versions='<1.0.0',
                description='This is an error',
            ),
            Vulnerability(
                type='python',
                dependency='otherlib',
                installed_version='1.4.0',
                affected_versions='<2.0.0',
                description='This is also an error',
            ),
        ])

    def test_get_python_vulnerabilities_cannot_parse_output(self, mock_popen):
        cmd = Command()
        output = '{invalid5:52"json2'
        mock_popen(255, output=output)

        with pytest.raises(DependencySecurityCheckFailed) as err:
            cmd.get_python_vulnerabilities()
        assert err.value.args[0] == 'Could not parse pyup safety output'

    def test_get_javascript_vulnerabilities_none(self, mock_popen):
        cmd = Command()
        popen = mock_popen(0)

        assert cmd.get_javascript_vulnerabilities() == []
        assert popen.call_args[0][0] == [
            settings.NPM_PATH,
            'audit',
            '--json',
        ]
        assert popen.call_args[1]['cwd'] == os.path.dirname(settings.PACKAGE_JSON_PATH)

    def test_get_javascript_vulnerabilities_failure(self, mock_popen):
        """Handle failures like being unable to connect to the network."""
        cmd = Command()
        error_output = 'pretend-im-a-traceback'
        mock_popen(5, error_output='pretend-im-a-traceback')

        with pytest.raises(DependencySecurityCheckFailed) as err:
            cmd.get_javascript_vulnerabilities()
        assert err.value.args[0] == error_output

    def test_get_javascript_vulnerabilities_found(self, mock_popen):
        cmd = Command()

        # Adapated from npm audit output for a jest issue
        output = json.dumps({
            "actions": [
                # Skipping actions because we don't do anything with them.
            ],
            "advisories": {
                "111": {
                    "findings": [
                        {
                            "version": "1.0.0",
                            "paths": [
                                "foo>foo-cli>pants"
                            ],
                            "dev": True,
                            "optional": False,
                            "bundled": False
                        }
                    ],
                    "id": 722,
                    "created": "2018-11-05T17:04:20.221Z",
                    "updated": "2018-11-05T17:04:20.221Z",
                    "deleted": None,
                    "title": "Prototype pollution",
                    "found_by": {
                        "link": "",
                        "name": "jeff"
                    },
                    "reported_by": {
                        "link": "",
                        "name": "jeff"
                    },
                    "module_name": "pants",
                    "cves": [
                        "CVE-2018-42"
                    ],
                    "vulnerable_versions": "<=1.0.0",
                    "patched_versions": ">=1.0.1",
                    "overview": "Versions of `pants` before 1.0.0 have problems.",
                    "recommendation": "Update to version 1.0.1 or later.",
                    "references": "- [report](https://example.com/)",
                    "access": "public",
                    "severity": "low",
                    "cwe": "CWE-42",
                    "metadata": {
                        "module_type": "",
                        "exploitability": 2,
                        "affected_components": "recursive leggings"
                    },
                    "url": "https://example.com/advisories/42"
                }
            },
            "muted": [],
            "metadata": {
                "vulnerabilities": {
                    "info": 0,
                    "low": 9,
                    "moderate": 0,
                    "high": 0,
                    "critical": 0
                },
                "dependencies": 271,
                "devDependencies": 29443,
                "optionalDependencies": 550,
                "totalDependencies": 29714
            },
            "runId": "6eaec258-cf71-43b7-95df-7ba256ecf1c2"
        })
        mock_popen(1, output=output)

        assert set(cmd.get_javascript_vulnerabilities()) == set([
            Vulnerability(
                type='javascript',
                dependency='pants',
                installed_version='1.0.0',
                affected_versions='<=1.0.0',
                description='https://example.com/advisories/42',
            ),
        ])

    def test_get_javascript_vulnerabilities_cannot_parse_output(self, mock_popen):
        cmd = Command()
        output = '{invalid5:52"json2'
        mock_popen(1, output=output)

        with pytest.raises(DependencySecurityCheckFailed) as err:
            cmd.get_javascript_vulnerabilities()
        assert err.value.args[0] == 'Could not parse nsp output'

    @pytest.mark.parametrize('option', ('NPM_PATH', 'SAFETY_PATH', 'PACKAGE_JSON_PATH'))
    def test_run_option_validation(self, option, tmpdir):
        cmd = Command()

        # Error if the config option is missing
        with override_settings(**{option: None}):
            with pytest.raises(CommandError):
                cmd.validate_options()

        # Error if the config option points to a nonexistant file
        with override_settings(**{option: tmpdir.join('does.not.exist').strpath}):
            with pytest.raises(CommandError):
                cmd.validate_options()

        # Error if the config option points to a directory
        with override_settings(**{option: tmpdir.join('directory').strpath}):
            with pytest.raises(CommandError):
                cmd.validate_options()

        # No error if the config option points to an existing file
        tmpdir.join('directory').mkdir()
        tmpdir.join('binary').write('fake binary')
        with override_settings(**{option: tmpdir.join('binary').strpath}):
            cmd.validate_options()

    def test_run_log(self):
        """Alert via logging if there's no Sentry DSN configured."""
        cmd = Command()
        vuln = Vulnerability(
            type='python',
            dependency='mylibrary',
            installed_version='0.9.0',
            affected_versions='<1.0.0',
            description='This is an error',
        )

        with mock.patch.object(cmd, 'get_python_vulnerabilities', return_value=[vuln]):
            with mock.patch.object(cmd, 'get_javascript_vulnerabilities', return_value=[]):
                with mock.patch.object(cmd, 'alert_log'):
                    cmd.handle()
                    cmd.alert_log.assert_called_with([vuln])

    def test_run_sentry(self):
        """Alert Sentry if there's a DSN configured."""
        dsn = 'https://foo:bar@example.com/123456'
        with override_settings(RAVEN_DSN=dsn):
            cmd = Command()
            vuln = Vulnerability(
                type='python',
                dependency='mylibrary',
                installed_version='0.9.0',
                affected_versions='<1.0.0',
                description='This is an error',
            )

            with mock.patch.object(cmd, 'get_python_vulnerabilities', return_value=[vuln]):
                with mock.patch.object(cmd, 'get_javascript_vulnerabilities', return_value=[]):
                    with mock.patch.object(cmd, 'alert_sentry'):
                        cmd.handle()
                        cmd.alert_sentry.assert_called_with(dsn, [vuln])
