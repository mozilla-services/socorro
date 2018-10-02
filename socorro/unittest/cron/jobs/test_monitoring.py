import json
import os

import pytest
import mock
from configman.config_exceptions import OptionError
from configman.dotdict import DotDict

from socorro.cron.jobs.monitoring import (
    DependencySecurityCheckCronApp,
    DependencySecurityCheckFailed,
    Vulnerability,
)


@pytest.fixture
def app_config(tmpdir):
    config = {}
    for key in ('nsp_path', 'safety_path', 'package_json_path'):
        path = tmpdir.join(key)
        path.write('fake file', ensure=True)
        config[key] = path.strpath

    return config


@pytest.fixture
def mock_popen():
    popen_patch = mock.patch('socorro.cron.jobs.monitoring.Popen')
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
class TestDependencySecurityCheckCronApp(object):
    def get_app(self, config=None):
        config = DotDict(config or {})
        return DependencySecurityCheckCronApp(config, None)

    def test_get_python_vulnerabilities_none(self, mock_popen, app_config):
        app = self.get_app(app_config)
        popen = mock_popen(0)

        assert app.get_python_vulnerabilities() == []
        assert popen.call_args[0][0] == [app_config['safety_path'], 'check', '--json']

    def test_get_python_vulnerabilities_with_key(self, mock_popen, app_config):
        app_config['safety_api_key'] = 'fake-api-key'
        app = self.get_app(app_config)
        popen = mock_popen(0)

        assert app.get_python_vulnerabilities() == []
        assert popen.call_args[0][0] == [
            app_config['safety_path'],
            'check',
            '--json',
            '--key',
            'fake-api-key',
        ]

    def test_get_python_vulnerabilities_failure(self, mock_popen, app_config):
        """Handle failures like being unable to connect to the network.

        """
        app = self.get_app(app_config)
        error_output = 'pretend-im-a-traceback'
        mock_popen(1, error_output='pretend-im-a-traceback')

        with pytest.raises(DependencySecurityCheckFailed) as err:
            app.get_python_vulnerabilities()
        assert err.value.args[0] == error_output

    def test_get_python_vulnerabilities_found(self, mock_popen, app_config):
        app = self.get_app(app_config)

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

    def test_get_python_vulnerabilities_cannot_parse_output(self, mock_popen, app_config):
        app = self.get_app(app_config)
        output = '{invalid5:52"json2'
        mock_popen(255, output=output)

        with pytest.raises(DependencySecurityCheckFailed) as err:
            app.get_python_vulnerabilities()
        assert err.value.args[0] == 'Could not parse pyup safety output'

    def test_get_javascript_vulnerabilities_none(self, mock_popen, app_config):
        app = self.get_app(app_config)
        popen = mock_popen(0)

        assert app.get_javascript_vulnerabilities() == []
        assert popen.call_args[0][0] == [
            app_config['nsp_path'],
            'check',
            '--reporter=json',
        ]
        assert popen.call_args[1]['cwd'] == os.path.dirname(app_config['package_json_path'])

    def test_get_javascript_vulnerabilities_failure(self, mock_popen, app_config):
        """Handle failures like being unable to connect to the network.

        """
        app = self.get_app(app_config)
        error_output = 'pretend-im-a-traceback'
        mock_popen(5, error_output='pretend-im-a-traceback')

        with pytest.raises(DependencySecurityCheckFailed) as err:
            app.get_javascript_vulnerabilities()
        assert err.value.args[0] == error_output

    def test_get_javascript_vulnerabilities_found(self, mock_popen, app_config):
        app = self.get_app(app_config)

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
        mock_popen(1, output=output)

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

    def test_get_javascript_vulnerabilities_cannot_parse_output(self, mock_popen, app_config):
        app = self.get_app(app_config)
        output = '{invalid5:52"json2'
        mock_popen(1, output=output)

        with pytest.raises(DependencySecurityCheckFailed) as err:
            app.get_javascript_vulnerabilities()
        assert err.value.args[0] == 'Could not parse nsp output'

    @pytest.mark.parametrize('option', ('nsp_path', 'safety_path', 'package_json_path'))
    def test_run_option_validation(self, option, tmpdir, app_config):
        # Error if the config option is missing
        del app_config[option]
        app = self.get_app(app_config)
        with pytest.raises(OptionError):
            app.validate_options()

        # Error if the config option points to a nonexistant file
        app_config[option] = tmpdir.join('does.not.exist').strpath
        app = self.get_app(app_config)
        with pytest.raises(OptionError):
            app.validate_options()

        # Error if the config option points to a directory
        app_config[option] = tmpdir.join('directory').strpath
        app = self.get_app(app_config)
        with pytest.raises(OptionError):
            app.validate_options()

        # No error if the config option points to an existing file
        tmpdir.join('directory').mkdir()
        tmpdir.join('binary').write('fake binary')
        app_config[option] = tmpdir.join('binary').strpath
        app = self.get_app(app_config)
        app.validate_options()

    def test_run_log(self, app_config):
        """Alert via logging if there's no Sentry DSN configured."""
        app = self.get_app(app_config)
        vuln = Vulnerability(
            type='python',
            dependency='mylibrary',
            installed_version='0.9.0',
            affected_versions='<1.0.0',
            description='This is an error',
        )

        with mock.patch.object(app, 'get_python_vulnerabilities', return_value=[vuln]):
            with mock.patch.object(app, 'get_javascript_vulnerabilities', return_value=[]):
                with mock.patch.object(app, 'alert_log'):
                    app.run()
                    app.alert_log.assert_called_with([vuln])

    def test_run_raven(self, app_config):
        """Alert via Raven if there's a Sentry DSN configured."""
        dsn = 'https://foo:bar@example.com/123456'
        app_config['sentry.dsn'] = dsn
        app = self.get_app(app_config)
        vuln = Vulnerability(
            type='python',
            dependency='mylibrary',
            installed_version='0.9.0',
            affected_versions='<1.0.0',
            description='This is an error',
        )

        with mock.patch.object(app, 'get_python_vulnerabilities', return_value=[vuln]):
            with mock.patch.object(app, 'get_javascript_vulnerabilities', return_value=[]):
                with mock.patch.object(app, 'alert_sentry'):
                    app.run()
                    app.alert_sentry.assert_called_with(dsn, [vuln])
