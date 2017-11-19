import json
from contextlib import contextmanager, nested

import pytest
import mock
from configman.dotdict import DotDict

from socorro.cron.jobs.monitoring import (
    DependencySecurityCheckCronApp,
    DependencySecurityCheckFailed,
    Vulnerability,
)
from socorro.unittest.cron.jobs.base import IntegrationTestBase


# Ideally this'd be a pytest yielding fixture, but fixtures aren't easily used
# with unittest.TestCase subclasses.
@contextmanager
def mock_popen(return_code, output='', error_output=''):
    popen_patch = mock.patch('socorro.cron.jobs.monitoring.Popen')
    popen = popen_patch.start()

    process = popen.return_value
    process.returncode = return_code
    process.communicate.return_value = (output, error_output)

    yield popen

    popen_patch.stop()


# Mocking Popen for multiple calls in a row is kinda hairy, so instead
# we're testing the separate get_*_vulnerabilities methods and then
# mocking them to test the main command.
class TestDependencySecurityCheckCronApp(IntegrationTestBase):
    def get_app(self, config=None):
        config = DotDict(config or {})
        return DependencySecurityCheckCronApp(config, None)

    def test_get_python_vulnerabilities_none(self):
        app = self.get_app()

        with mock_popen(0) as popen:
            assert app.get_python_vulnerabilities() == []
            assert popen.call_args[0][0] == ['safety', 'check', '--json']

    def test_get_python_vulnerabilities_failure(self):
        """Handle failures like being unable to connect to the network.

        """
        app = self.get_app()

        error_output = 'pretend-im-a-traceback'
        with mock_popen(1, error_output='pretend-im-a-traceback'):
            with pytest.raises(DependencySecurityCheckFailed) as err:
                app.get_python_vulnerabilities()
            assert err.value.args[0] == error_output

    def test_get_python_vulnerabilities_found(self):
        app = self.get_app()

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

        with mock_popen(255, output=output):
            assert set(app.get_python_vulnerabilities()) == set([
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

    def test_get_python_vulnerabilities_cannot_parse_output(self):
        app = self.get_app()
        output = '{invalid5:52"json2'

        with mock_popen(255, output=output):
            with pytest.raises(DependencySecurityCheckFailed) as err:
                app.get_python_vulnerabilities()
            assert err.value.args[0] == 'Could not parse pyup safety output'

    def test_get_javascript_vulnerabilities_none(self):
        app = self.get_app({
            'node_modules': '/fake/node_modules',
        })

        with mock_popen(0) as popen:
            assert app.get_javascript_vulnerabilities() == []
            assert popen.call_args[0][0] == [
                '/fake/node_modules/.bin/nsp',
                'check',
                '--reporter=json',
            ]

    def test_get_javascript_vulnerabilities_failure(self):
        """Handle failures like being unable to connect to the network.

        """
        app = self.get_app({
            'node_modules': '/fake/node_modules',
        })

        error_output = 'pretend-im-a-traceback'
        with mock_popen(5, error_output='pretend-im-a-traceback'):
            with pytest.raises(DependencySecurityCheckFailed) as err:
                app.get_javascript_vulnerabilities()
            assert err.value.args[0] == error_output

    def test_get_javascript_vulnerabilities_found(self):
        app = self.get_app({
            'node_modules': '/fake/node_modules',
        })

        # Adapated from nsp output for a jquery issue
        output = json.dumps([
            {
                'id': 328,
                'updated_at': '2017-04-20T04:19:42.040Z',
                'created_at': '2017-03-20T21:50:28.000Z',
                'publish_date': '2017-03-21T18:23:53.000Z',
                'overview': 'This is an error',
                'recommendation': 'Upgrade to v3.0.0 or greater.',
                'cvss_vector': 'CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:C/C:L/I:L/A:N',
                'cvss_score': 7.2,
                'module': 'mylibrary',
                'version': '0.9.0',
                'vulnerable_versions': '<1.0.0',
                'patched_versions': '>=3.0.0',
                'title': 'Cross-Site Scripting (XSS)',
                'path': [
                    'socorro-webapp-django@0.0.0',
                    'jquery@2.1.0',
                ],
                'advisory': 'https://nodesecurity.io/advisories/328',
            },
            {
                'id': 327,
                'updated_at': '2017-04-20T04:19:42.040Z',
                'created_at': '2017-03-20T21:50:28.000Z',
                'publish_date': '2017-03-21T18:23:53.000Z',
                'overview': 'This is also an error',
                'recommendation': 'Upgrade to v3.0.0 or greater.',
                'cvss_vector': 'CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:C/C:L/I:L/A:N',
                'cvss_score': 7.2,
                'module': 'otherlib',
                'version': '1.4.0',
                'vulnerable_versions': '<2.0.0',
                'patched_versions': '>=3.0.0',
                'title': 'Cross-Site Scripting (XSS)',
                'path': [
                    'socorro-webapp-django@0.0.0',
                    'jquery@2.1.0',
                ],
                'advisory': 'https://nodesecurity.io/advisories/327',
            },
        ])

        with mock_popen(1, output=output):
            assert set(app.get_javascript_vulnerabilities()) == set([
                Vulnerability(
                    type='javascript',
                    dependency='mylibrary',
                    installed_version='0.9.0',
                    affected_versions='<1.0.0',
                    description='https://nodesecurity.io/advisories/328',
                ),
                Vulnerability(
                    type='javascript',
                    dependency='otherlib',
                    installed_version='1.4.0',
                    affected_versions='<2.0.0',
                    description='https://nodesecurity.io/advisories/327',
                ),
            ])

    def test_get_javascript_vulnerabilities_cannot_parse_output(self):
        app = self.get_app({
            'node_modules': '/fake/node_modules',
        })
        output = '{invalid5:52"json2'

        with mock_popen(1, output=output):
            with pytest.raises(DependencySecurityCheckFailed) as err:
                app.get_javascript_vulnerabilities()
            assert err.value.args[0] == 'Could not parse nsp output'

    def test_run_log(self):
        """Alert via logging if there's no Sentry DSN configured."""
        app = self.get_app()
        vuln = Vulnerability(
            type='python',
            dependency='mylibrary',
            installed_version='0.9.0',
            affected_versions='<1.0.0',
            description='This is an error',
        )

        mocks = [
            mock.patch.object(app, 'get_python_vulnerabilities', return_value=[vuln]),
            mock.patch.object(app, 'get_javascript_vulnerabilities', return_value=[]),
            mock.patch.object(app, 'alert_log'),
        ]

        with nested(*mocks):
            app.run()
            app.alert_log.assert_called_with([vuln])

    def test_run_raven(self):
        """Alert via Raven if there's a Sentry DSN configured."""
        dsn = 'https://foo:bar@example.com/123456'
        app = self.get_app({
            'sentry.dsn': dsn,
        })
        vuln = Vulnerability(
            type='python',
            dependency='mylibrary',
            installed_version='0.9.0',
            affected_versions='<1.0.0',
            description='This is an error',
        )

        mocks = [
            mock.patch.object(app, 'get_python_vulnerabilities', return_value=[vuln]),
            mock.patch.object(app, 'get_javascript_vulnerabilities', return_value=[]),
            mock.patch.object(app, 'alert_sentry'),
        ]

        with nested(*mocks):
            app.run()
            app.alert_sentry.assert_called_with(dsn, [vuln])
