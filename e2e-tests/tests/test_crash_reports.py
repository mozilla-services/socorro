# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from pages.home_page import CrashStatsHomePage


class TestCrashReports:

    _expected_products = [
        'Firefox',
        'Thunderbird',
        'SeaMonkey',
        'FennecAndroid']

    @pytest.mark.nondestructive
    @pytest.mark.parametrize(('product'), [
        'Firefox',
        'Thunderbird',
        'SeaMonkey',
        'FennecAndroid'])
    def test_that_reports_form_has_same_product(self, base_url, selenium, product):
        csp = CrashStatsHomePage(selenium, base_url).open()
        csp.header.select_product(product)
        assert product in selenium.title

        crash_per_day = csp.header.select_report('Crashes per Day')
        assert crash_per_day.page_heading == selenium.title
        assert crash_per_day.header.current_product == crash_per_day.product_select

    @pytest.mark.nondestructive
    @pytest.mark.parametrize(('product'), [
        'Firefox',
        'Thunderbird',
        'SeaMonkey',
        'FennecAndroid'])
    def test_that_current_version_selected_in_top_crashers_header(self, base_url, selenium, product):
        csp = CrashStatsHomePage(selenium, base_url).open()
        csp.header.select_product(product)
        cstc = csp.header.select_report('Top Crashers')
        cstc.header.select_version('Current Versions')

        assert product == cstc.page_heading_product
        assert cstc.page_heading_version == cstc.header.current_version

    @pytest.mark.nondestructive
    def test_that_top_crasher_filter_all_return_results(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        product = csp.header.current_product
        cstc = csp.header.select_report('Top Crashers')
        if cstc.results_found:
            assert product == cstc.page_heading_product

        cstc.click_filter_by('All')
        assert cstc.results_count > 0

    @pytest.mark.nondestructive
    def test_that_top_crasher_filter_browser_return_results(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        product = csp.header.current_product
        cstc = csp.header.select_report('Top Crashers')
        if cstc.results_found:
            assert product == cstc.page_heading_product

        cstc.click_filter_by('Browser')
        assert cstc.results_count > 0

    @pytest.mark.nondestructive
    def test_that_top_crasher_filter_plugin_return_results(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        product = csp.header.current_product
        cstc = csp.header.select_report('Top Crashers')
        if cstc.results_found:
            assert product == cstc.page_heading_product

        cstc.click_filter_by('Plugin')
        assert cstc.results_count > 0

    @pytest.mark.nondestructive
    @pytest.mark.parametrize(('product'), _expected_products)
    def test_that_top_crashers_reports_links_work(self, base_url, selenium, product):
        csp = CrashStatsHomePage(selenium, base_url).open()
        csp.header.select_product(product)

        for i in range(len(csp.release_channels)):
            top_crasher_name = csp.release_channels[i].product_version_label
            top_crasher_page = csp.release_channels[i].click_top_crasher()
            top_crasher_page.wait_for_page_to_load()
            assert top_crasher_name in top_crasher_page.page_heading
            selenium.back()
            csp.wait_for_page_to_load()

    @pytest.mark.nondestructive
    def test_top_crasher_reports_tab_has_uuid_report(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        top_crashers = csp.release_channels[-1].click_top_crasher()
        crash_signature = top_crashers.click_first_signature()
        crash_signature.click_reports_tab()
        reports_table_count = len(crash_signature.reports)

        # verify crash reports table is populated
        assert crash_signature.results_count_total > 0
        assert reports_table_count > 0, 'No reports found'

        most_recent_report = crash_signature.reports[0]
        uuid_report = most_recent_report.click_report_date()

        # verify the uuid report page
        assert '' != uuid_report.uuid_in_body, 'UUID not found in body'
        assert '' != uuid_report.uuid_in_table, 'UUID not found in table'
        assert '' != uuid_report.signature_in_body, 'Signature not found in body'
        assert '' != uuid_report.signature_in_table, 'Signature not found in table'
        assert (uuid_report.uuid_in_body == uuid_report.uuid_in_table), \
            'UUID in body did not match the UUID in the table'
        assert (uuid_report.signature_in_body in uuid_report.signature_in_table), \
            'Signature in body did not match the signature in the '

    @pytest.mark.nondestructive
    @pytest.mark.parametrize(('product'), [
        'Firefox',
        pytest.mark.xfail("'allizom.org' in config.getvalue('base_url')", reason='bug 1299916')('Thunderbird'),
        'SeaMonkey',
        'FennecAndroid'])
    def test_the_product_releases_return_results(self, base_url, selenium, product):
        csp = CrashStatsHomePage(selenium, base_url).open()
        csp.header.select_product(product)

        for i in range(len(csp.release_channels)):
            top_crasher_page = csp.release_channels[i].click_top_crasher()
            if top_crasher_page.no_results_text is not False:
                assert 'Range by Report Date instead?' in top_crasher_page.no_results_text
            else:
                assert top_crasher_page.results_found, 'No results found'
            selenium.back()
            csp.wait_for_page_to_load()

    @pytest.mark.nondestructive
    def test_that_7_days_is_selected_default_for_nightlies(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        top_crashers = csp.release_channels
        tc_page = top_crashers[1].click_top_crasher()

        assert '7' == tc_page.current_days_filter

    @pytest.mark.nondestructive
    def test_that_only_browser_reports_have_browser_icon(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        reports_page = csp.release_channels[-1].click_top_crasher()
        product_type, days, os = 'Browser', '7', 'Windows'
        assert product_type == reports_page.current_filter_type

        reports_page.click_filter_days_by(days)
        reports_page.click_filter_os_by(os)
        assert product_type == reports_page.current_filter_type
        assert days == reports_page.current_days_filter
        assert os == reports_page.current_os_filter

        signature_list_items = reports_page.random_signature_items(19)
        assert len(signature_list_items) > 0, 'Signature list items not found'

        for signature_item in signature_list_items:
            assert (signature_item.is_browser_icon_visible), \
                "Signature %s did not have a browser icon" % signature_item.title
            assert (not signature_item.is_plugin_icon_visible), \
                "Signature %s unexpectedly had a plugin icon" % signature_item.title

    @pytest.mark.nondestructive
    def test_that_only_plugin_reports_have_plugin_icon(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        reports_page = csp.release_channels[-1].click_top_crasher()
        product_type, days, os = 'Plugin', '28', 'Windows'
        reports_page.click_filter_by(product_type)
        reports_page.click_filter_days_by(days)
        reports_page.click_filter_os_by(os)
        assert product_type == reports_page.current_filter_type
        assert days == reports_page.current_days_filter
        assert os == reports_page.current_os_filter

        signature_list_items = reports_page.signature_items

        assert len(signature_list_items) > 0, 'Signature list items not found'

        for signature_item in signature_list_items[:min(signature_list_items, 24)]:
            assert (signature_item.is_plugin_icon_visible), \
                "Signature %s did not have a plugin icon" % signature_item.title
            assert (not signature_item.is_browser_icon_visible), \
                "Signature %s unexpectedly had a browser icon" % signature_item.title

    @pytest.mark.nondestructive
    def test_that_lowest_version_topcrashers_do_not_return_errors(self, base_url, selenium):
        csp = CrashStatsHomePage(selenium, base_url).open()
        lowest_version_index = len(csp.header.version_select_text) - 1
        csp.header.select_version_by_index(lowest_version_index)
        cstc = csp.header.select_report('Top Crashers')
        cstc.click_filter_days_by('14')
        assert 'error' not in cstc.page_heading

        cstc.click_filter_by('Plugin')
        assert 'error' not in cstc.page_heading
