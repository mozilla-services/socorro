#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By

from pages.base_page import CrashStatsBasePage


class CrashStatsTopCrashersBySite(CrashStatsBasePage):

    _product_header_locator = (By.ID, 'tcburl-product')
    _product_version_header_locator = (By.ID, 'tcburl-version')

    @property
    def product_header(self):
        return self.find_element(*self._product_header_locator).text

    @property
    def product_version_header(self):
        return self.find_element(self._product_version_header_locator).text
