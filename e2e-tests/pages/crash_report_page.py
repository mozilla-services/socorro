#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pypom import Region
from selenium.webdriver.common.by import By

from pages.base_page import CrashStatsBasePage


class CrashReport(CrashStatsBasePage):

    _reports_tab_locator = (By.ID, 'reports')
    _results_count_locator = (By.CSS_SELECTOR, 'span.totalItems')
    _reports_row_locator = (By.CSS_SELECTOR, '#reports-list tbody tr')
    _report_tab_button_locator = (By.CSS_SELECTOR, '#panels-nav .reports')
    _summary_table_locator = (By.CSS_SELECTOR, '.content')

    def wait_for_page_to_load(self):
        super(CrashReport, self).wait_for_page_to_load()
        self.wait.until(lambda s: self.is_element_displayed(*self._summary_table_locator))
        return self

    @property
    def reports(self):
        return [self.Report(self, el) for el in self.find_elements(*self._reports_row_locator)]

    @property
    def results_count_total(self):
        return int(self.find_element(*self._results_count_locator).text.replace(",", ""))

    def click_reports_tab(self):
        self.find_element(*self._report_tab_button_locator).click()
        self.wait.until(lambda s: len(self.reports))

    class Report(Region):

        _product_locator = (By.CSS_SELECTOR, 'td:nth-of-type(3)')
        _version_locator = (By.CSS_SELECTOR, 'td:nth-of-type(4)')
        _report_date_link_locator = (By.CSS_SELECTOR, '#reports-list a.external-link')

        @property
        def product(self):
            return self.find_element(*self._product_locator).text

        @property
        def version(self):
            return self.find_element(*self._version_locator).text

        def click_report_date(self):
            self.find_element(*self._report_date_link_locator).click()
            from uuid_report import UUIDReport
            return UUIDReport(self.selenium, self.page.base_url).wait_for_page_to_load()
