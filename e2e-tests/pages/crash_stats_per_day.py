#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from pages.base_page import CrashStatsBasePage


class CrashStatsPerDay(CrashStatsBasePage):

    _product_select_locator = (By.ID, 'daily_search_version_form_products')
    _date_start_locator = (By.CSS_SELECTOR, '.daily_search_body .date[name="date_start"]')
    _generate_button_locator = (By.ID, 'daily_search_version_form_submit')
    _table_locator = (By.ID, 'crash_data')
    _row_table_locator = (By.CSS_SELECTOR, '#crash_data > tbody > tr')

    @property
    def product_select(self):
        element = self.find_element(*self._product_select_locator)
        select = Select(element)
        return select.first_selected_option.text

    def type_start_date(self, date):
        date_element = self.find_element(*self._date_start_locator)
        date_element.clear()
        date_element.send_keys(date)

    def click_generate_button(self):
        self.find_element(*self._generate_button_locator).click()

    @property
    def is_table_visible(self):
        return self.is_element_displayed(None, *self._table_locator)

    @property
    def table_row_count(self):
        return len(self.find_elements(self._row_table_locator))

    @property
    def last_row_date_value(self):
        return self.find_elements(*self._row_table_locator)[:1].text
