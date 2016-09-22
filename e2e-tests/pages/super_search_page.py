#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from pypom import Region
from pages.base_page import CrashStatsBasePage


class CrashStatsSuperSearch(CrashStatsBasePage):

    _page_title = 'Search - Mozilla Crash Reports'
    _page_loaded_locator = (By.CSS_SELECTOR, '#s2id_simple-product input')
    _advanced_search_loaded_locator = (By.CSS_SELECTOR, '#advanced-search .select2-container-active')
    _search_button_locator = (By.ID, 'search-button')

    # Simple Search
    _simple_search_product_field_locator = (By.CSS_SELECTOR, '#s2id_simple-product input')
    _simple_search_version_field_locator = (By.CSS_SELECTOR, '#s2id_simple-version input')
    _simple_search_platform_field_locator = (By.CSS_SELECTOR, '#s2id_simple-platform input')
    _simple_search_platform_text_locator = (By.CSS_SELECTOR, '#s2id_simple-product .select2-choices li div')

    # Advanced Search
    _new_line_button_locator = (By.CSS_SELECTOR, 'button.new-line')
    _highlighted_text_locator = (By.CSS_SELECTOR, 'li[class*="highlighted"]')
    _facet_text_locator = (By.CSS_SELECTOR, '#advanced-search fieldset[id="%s"] > div:nth-child(2) span:first-child')
    _facet_field_locator = (By.CSS_SELECTOR, '#advanced-search fieldset[id="%s"] .field')
    _operator_text_locator = (By.CSS_SELECTOR, '#advanced-search fieldset[id="%s"] > div:nth-child(4) span')
    _operator_field_locator = (By.CSS_SELECTOR, '#advanced-search fieldset[id="%s"] .operator')
    _match_field_locator = (By.CSS_SELECTOR, '#advanced-search fieldset[id="%s"] .select2-search-field input')
    _match_text_locator = (By.CSS_SELECTOR, '#advanced-search fieldset[id="%s"] > div:nth-child(6) div')

    # More options section
    _more_options_locator = (By.CSS_SELECTOR, '.options h4')
    _more_options_facet_text_locator = (By.CSS_SELECTOR, '#s2id__facets ul li div')
    _delete_facet_locator = (By.CSS_SELECTOR, '#s2id__facets a.select2-search-choice-close')
    _input_facet_locator = (By.CSS_SELECTOR, '#s2id__facets ul input')
    _facet_name_suggestion_locator = (By.CSS_SELECTOR, '.select2-result-label')

    # Search results section
    _error_text_locator = (By.CSS_SELECTOR, '.errorlist li li')
    _results_facet_locator = (By.CSS_SELECTOR, '#search_results-nav li:nth-child(2) span')
    _column_list_locator = (By.CSS_SELECTOR, '#s2id__columns_fake ul li.select2-search-choice')
    _table_row_locator = (By.CSS_SELECTOR, '#reports-list tbody tr')
    _loader_locator = (By.CLASS_NAME, 'loader')
    _crash_reports_tab_locator = (By.CSS_SELECTOR, '#search_results-nav [href="#crash-reports"] span')

    def wait_for_page_to_load(self):
        super(CrashStatsSuperSearch, self).wait_for_page_to_load()
        self.wait.until(lambda s: self.is_element_displayed(*self._page_loaded_locator))
        return self

    # Simple Search form fields

    def select_product(self, product):
        self.find_element(*self._simple_search_product_field_locator).send_keys(product)

    def select_version(self, version):
        self.find_element(*self._simple_search_version_field_locator).send_keys(version)

    def select_platform(self, platform):
        el = self.find_element(*self._simple_search_platform_field_locator)
        el.send_keys(platform)
        el.send_keys(Keys.RETURN)

    @property
    def selected_products(self):
        return self.find_element(*self._simple_search_platform_text_locator).text

    # Advanced Search form fields

    def click_new_line(self):
        ''' Opens up the advanced search field options '''
        self.find_element(*self._new_line_button_locator).click()
        self.wait.until(lambda s: self.is_element_present(*self._advanced_search_loaded_locator))

    def select_facet(self, line_id, field):
        input_locator = (self._facet_field_locator[0], self._facet_field_locator[1] % line_id)
        self.wait.until(lambda s: self.is_element_present(*input_locator))
        facet_field = self.find_element(*input_locator)
        facet_field.send_keys(field)
        self.wait.until(lambda s: self.is_element_present(*self._highlighted_text_locator))
        facet_field.send_keys(Keys.RETURN)

    def select_operator(self, line_id, operator):
        input_locator = (self._operator_field_locator[0], self._operator_field_locator[1] % line_id)
        self.wait.until(lambda s: self.is_element_present(*input_locator))
        operator_field = self.find_element(*input_locator)
        operator_field.send_keys(operator)
        self.wait.until(lambda s: self.is_element_present(*self._highlighted_text_locator))
        operator_field.send_keys(Keys.RETURN)

    def select_match(self, line_id, match):
        input_locator = (self._match_field_locator[0], self._match_field_locator[1] % line_id)
        self.wait.until(lambda s: self.is_element_present(*input_locator))
        self.find_element(*input_locator).send_keys(match)
        self.wait.until(lambda s: self.is_element_present(*self._highlighted_text_locator))
        self.find_element(*self._highlighted_text_locator).click()

    def field(self, line_id):
        return self.find_element(self._facet_text_locator[0], self._facet_text_locator[1] % line_id).text

    def operator(self, line_id):
        return self.find_element(self._operator_text_locator[0], self._operator_text_locator[1] % line_id).text

    def match(self, line_id):
        return self.find_element(self._match_text_locator[0], self._match_text_locator[1] % line_id).text

    @property
    def error(self):
        return self.find_element(*self._error_text_locator).text

    def click_search(self):
        self.find_element(*self._search_button_locator).click()
        self.wait.until(lambda s: not self.is_element_present(*self._loader_locator))

    def click_more_options(self):
        self.find_element(*self._more_options_locator).click()

    def click_crash_reports_tab(self):
        self.wait.until(lambda s: self.is_element_displayed(*self._crash_reports_tab_locator))
        self.find_element(*self._crash_reports_tab_locator).click()

    # More options section
    @property
    def more_options_facet(self):
        return self.selenium.find_element(*self._more_options_facet_text_locator).text

    def more_options_select_facet(self, facet):
        self.find_element(*self._input_facet_locator).click()
        self.find_element(*self._input_facet_locator).send_keys(facet)
        self.find_element(*self._facet_name_suggestion_locator).click()

    def more_options_delete_facet(self):
        self.find_element(*self._delete_facet_locator).click()
        self.wait.until(lambda s: not self.is_element_present(*self._delete_facet_locator))

    # Search results section
    @property
    def search_results_table_header(self):
        return self.SearchResultHeader(self)

    @property
    def columns(self):
        return[self.Column(self, el) for el in self.find_elements(*self._column_list_locator)]

    @property
    def search_results(self):
        return [self.SearchResult(self, el) for el in self.find_elements(*self._table_row_locator)]

    @property
    def are_search_results_found(self):
        return len(self.search_results) > 0

    def wait_for_column_deleted(self, number_of_expected_columns):
        self.wait.until(lambda s: number_of_expected_columns == len(self.columns))

    def wait_for_facet_in_results(self, facet):
        self.wait.until(lambda s: facet.lower() in self.results_facet.lower())

    @property
    def results_facet(self):
        return self.find_element(*self._results_facet_locator).text

    def is_column_in_list(self, column_name):
        return column_name in [column.column_name for column in self.columns]

    class SearchResultHeader(Region):

        _table_header_name_locator = (By.CSS_SELECTOR, '#reports-list thead th')

        @property
        def table_column_names(self):
            return [el.text.lower() for el in self.find_elements(*self._table_header_name_locator)]

        def is_column_not_present(self, column_name):
            self.wait.until(
                lambda s: column_name not in self.table_column_names, message='Column %s found in table header.' % column_name)
            return True

    class Column(Region):

        _column_name_locator = (By.CSS_SELECTOR, 'div')
        _column_delete_locator = (By.CSS_SELECTOR, 'a')

        @property
        def column_name(self):
            self.wait.until(lambda s: self.is_element_displayed(*self._column_name_locator))
            return self.find_element(*self._column_name_locator).text

        def delete_column(self):
            self.find_element(*self._column_delete_locator).click()

    class SearchResult(Region):

        _columns_locator = (By.CSS_SELECTOR, 'td')

        @property
        def _columns(self):
            return self.find_elements(*self._columns_locator)
