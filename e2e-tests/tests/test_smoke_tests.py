# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
import urllib

from pages.home_page import CrashStatsHomePage


class TestSmokeTests:

    _expected_products = ['Firefox',
                          'Thunderbird',
                          'SeaMonkey',
                          'FennecAndroid']
    _exploitability_url = '/exploitability/?product=Firefox'

    @pytest.mark.nondestructive
    def test_that_bugzilla_link_contain_current_site(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        path = '/invalidpath'
        csp.selenium.get(base_url + path)

        assert 'bug_file_loc=%s%s' % (base_url, path) in urllib.unquote(csp.link_to_bugzilla)

    @pytest.mark.nondestructive
    def test_that_exploitable_crash_report_not_displayed_for_not_logged_in_users(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        assert 'Exploitable Crashes' not in csp.header.report_list
        csp.selenium.get(base_url + self._exploitability_url)
        assert 'Login Required' in csp.page_heading

    def test_non_privileged_accounts_cannot_view_exploitable_crash_reports(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        csp.footer.login()
        assert csp.footer.is_logged_in
        assert 'Exploitable Crashes' not in csp.header.report_list
        csp.selenium.get(base_url + self._exploitability_url)
        assert 'Insufficient Privileges' in csp.page_heading
        csp.footer.logout()
        assert csp.footer.is_logged_out
