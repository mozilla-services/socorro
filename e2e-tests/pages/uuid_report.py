#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By

from pages.base_page import CrashStatsBasePage


class UUIDReport(CrashStatsBasePage):

    # https://crash-stats.mozilla.com/report/index/<UUID>
    _body_uuid_locator = (By.CSS_SELECTOR, '#mainbody #report-header-details code:nth-of-type(1)')
    _body_signature_locator = (By.CSS_SELECTOR, '#mainbody #report-header-details code:nth-of-type(2)')

    _table_locator = (By.CSS_SELECTOR, 'table.data-table')
    _table_uuid_locator = (By.CSS_SELECTOR, '#report-index tbody tr:nth-of-type(2) td')
    _table_signature_locator = (By.CSS_SELECTOR, '#report-index tbody tr:nth-of-type(1) td')

    @property
    def uuid_in_body(self):
        return self.find_element(*self._body_uuid_locator).text

    @property
    def uuid_in_table(self):
        return self.find_element(*self._table_uuid_locator).text

    @property
    def signature_in_body(self):
        return self.find_element(*self._body_signature_locator).text

    @property
    def signature_in_table(self):
        return self.find_element(*self._table_signature_locator).text
