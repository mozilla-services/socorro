#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import random

from pypom import Region
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from pages.base_page import CrashStatsBasePage


class CrashStatsTopCrashers(CrashStatsBasePage):

    _page_heading_product_locator = (By.ID, 'current-product')
    _page_heading_version_locator = (By.ID, 'current-version')

    _filter_by_locator = (By.CSS_SELECTOR, '.tc-duration-type.tc-filter > li > a')
    _filter_days_by_locator = (By.CSS_SELECTOR, '.tc-duration-days.tc-filter > li > a')
    _filter_os_by_locator = (By.CSS_SELECTOR, '.tc-per-platform.tc-filter > li > a')
    _current_filter_type_locator = (By.CSS_SELECTOR, 'ul.tc-duration-type li a.selected')
    _current_days_filter_locator = (By.CSS_SELECTOR, 'ul.tc-duration-days li a.selected')
    _current_os_filter_locator = (By.CSS_SELECTOR, 'ul.tc-per-platform li a.selected')
    _no_results_locator = (By.CSS_SELECTOR, 'p.no-results')

    @property
    def _signature_table_row_locator(self):
        if self.current_os_filter == "All":
            return (By.CSS_SELECTOR, '#signature-list tbody tr')
        else:
            return (By.CSS_SELECTOR, '#peros-tbl tbody tr')

    @property
    def page_heading_product(self):
        return self.find_element(*self._page_heading_product_locator).text

    @property
    def page_heading_version(self):
        return self.find_element(*self._page_heading_version_locator).text

    @property
    def results_count(self):
        return len(self.find_elements(*self._signature_table_row_locator))

    @property
    def results_found(self):
        try:
            return self.results_count > 0
        except NoSuchElementException:
            return False

    @property
    def no_results_text(self):
        if self.is_element_present(*self._no_results_locator):
            return self.find_element(*self._no_results_locator).text
        else:
            return False

    def click_filter_by(self, option):
        for element in self.find_elements(*self._filter_by_locator):
            if element.text == option:
                element.click()
                return CrashStatsTopCrashers(self.selenium, self.base_url).wait_for_page_to_load()

    def click_filter_days_by(self, days):
        '''
            Click on the link with the amount of days you want to filter by
        '''
        for element in self.find_elements(*self._filter_days_by_locator):
            if element.text == days:
                element.click()
                return CrashStatsTopCrashers(self.selenium, self.base_url).wait_for_page_to_load()

    def click_filter_os_by(self, os):
        '''
            Click on the link with the OS you want to filter by
        '''
        for element in self.find_elements(*self._filter_os_by_locator):
            if element.text == os:
                element.click()
                return CrashStatsTopCrashers(self.selenium, self.base_url).wait_for_page_to_load()

    @property
    def current_filter_type(self):
        return self.find_element(*self._current_filter_type_locator).text

    @property
    def current_days_filter(self):
        return self.find_element(*self._current_days_filter_locator).text

    @property
    def current_os_filter(self):
        return self.find_element(*self._current_os_filter_locator).text

    @property
    def signature_items(self):
        return [self.SignatureItem(self, el) for el in self.find_elements(*self._signature_table_row_locator)]

    def random_signature_items(self, count):
        signature_items = self.signature_items
        random_signature_items = []
        for i in range(0, count):
            random_signature_items.append(random.choice(signature_items))
        return random_signature_items

    def click_first_signature(self):
        return self.signature_items[0].click()

    @property
    def first_signature_title(self):
        return self.signature_items[0].title

    class SignatureItem(Region):
        _signature_link_locator = (By.CSS_SELECTOR, 'a.signature')
        _browser_icon_locator = (By.CSS_SELECTOR, 'div img.browser')
        _plugin_icon_locator = (By.CSS_SELECTOR, 'div img.plugin')

        def click(self):
            self.find_element(*self._signature_link_locator).click()
            from pages.crash_report_page import CrashReport
            return CrashReport(self.selenium, self.page.base_url).wait_for_page_to_load()

        @property
        def title(self):
            return self.find_element(*self._signature_link_locator).get_attribute('title')

        @property
        def is_plugin_icon_visible(self):
            return self.is_element_displayed(*self._plugin_icon_locator)

        @property
        def is_browser_icon_visible(self):
            return self.is_element_displayed(*self._browser_icon_locator)
