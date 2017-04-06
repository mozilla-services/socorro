# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from pages.home_page import CrashStatsHomePage


class TestSuperSearch:

    @pytest.mark.nondestructive
    def test_super_search_page_is_loaded(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        cs_super = csp.header.click_super_search()
        assert cs_super._page_title == selenium.title

    @pytest.mark.nondestructive
    def test_search_change_facet(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        cs_super = csp.header.click_super_search()
        cs_super.click_search()

        assert cs_super.more_options_facet in cs_super.results_facet.lower()

        cs_super.click_more_options()
        cs_super.more_options_delete_facet()
        cs_super.more_options_select_facet('address')
        assert 'address' == cs_super.more_options_facet

        cs_super.click_search()
        # The facet in the results does not update immediately,
        # so wait for it to be the value we expect
        cs_super.wait_for_facet_in_results(cs_super.more_options_facet)

    @pytest.mark.nondestructive
    def test_search_change_column(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        cs_super = csp.header.click_super_search()
        cs_super.click_search()
        assert cs_super.are_search_results_found

        cs_super.click_more_options()

        # Delete all columns except the last one
        for column in cs_super.columns[:-1]:
            cs_super.click_crash_reports_tab()
            current_column = column.column_name
            assert current_column in cs_super.search_results_table_header.table_column_names

            number_of_columns = len(cs_super.columns)
            column.delete_column()
            cs_super.wait_for_column_deleted(number_of_columns - 1)
            assert cs_super.is_column_in_list(current_column) is not True

            cs_super.click_search()
            if len(cs_super.columns) > 1:
                cs_super.click_crash_reports_tab()
                assert cs_super.are_search_results_found
                assert cs_super.search_results_table_header.is_column_not_present(current_column)

        # verify simple search terms have persisted
        assert 'Firefox' == cs_super.selected_products
        assert cs_super.columns[0].column_name in cs_super.search_results_table_header.table_column_names

    @pytest.mark.nondestructive
    def test_search_with_one_line(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        cs_super = csp.header.click_super_search()
        cs_super.click_search()
        assert cs_super.are_search_results_found
        assert 'Firefox' == cs_super.selected_products

    @pytest.mark.nondestructive
    def test_search_with_multiple_lines(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        cs_super = csp.header.click_super_search()
        # Do an advanced search
        cs_super.click_new_line()
        cs_super.select_facet('0', 'release channel')
        cs_super.select_operator('0', 'has terms')
        cs_super.select_match('0', 'nightly')
        cs_super.click_search()
        assert cs_super.are_search_results_found
        # verify simple search terms have persisted
        assert 'Firefox' == cs_super.selected_products
        # verify advanced search terms have persisted
        assert 'release channel' == cs_super.field('0')
        assert 'has terms' == cs_super.operator('0')
        assert 'nightly' == cs_super.match('0')


class TestSearchForSpecificResults:

    @pytest.mark.nondestructive
    def test_search_for_valid_signature(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        report_list = csp.release_channels[-1].click_top_crasher()
        signature = report_list.first_signature_title
        result = csp.header.search_for_crash(signature)

        assert result.are_search_results_found

    @pytest.mark.nondestructive
    def test_selecting_one_version_doesnt_show_other_versions(self, base_url, selenium):
        maximum_checks = 20  # limits the number of reports to check
        csp = CrashStatsHomePage(selenium, base_url).open()
        product = csp.header.current_product
        versions = csp.header.current_versions
        version = str(versions[1])
        csp.header.select_version(version)
        report_list = csp.release_channels[-1].click_top_crasher()
        crash_report_page = report_list.click_first_signature()
        crash_report_page.click_reports_tab()
        reports = crash_report_page.reports

        assert len(reports) > 0, 'reports not found for signature'

        random_indexes = csp.get_random_indexes(reports, maximum_checks)
        for index in random_indexes:
            report = reports[index]
            assert product == report.product
