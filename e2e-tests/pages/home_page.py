#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pypom import Region
from selenium.webdriver.common.by import By

from pages.base_page import CrashStatsBasePage


class CrashStatsHomePage(CrashStatsBasePage):

    URL_TEMPLATE = '/'

    _graph_loading_locator = (By.CSS_SELECTOR, '#homepage-graph .loading')
    _release_channels_locator = (By.CSS_SELECTOR, '.release_channel')

    def wait_for_page_to_load(self):
        super(CrashStatsHomePage, self).wait_for_page_to_load()
        self.wait.until(lambda s: not self.is_element_present(*self._graph_loading_locator))
        return self

    @property
    def release_channels(self):
        return [self.ReleaseChannels(self, el) for el in self.find_elements(*self._release_channels_locator)]

    class ReleaseChannels(Region):

        _release_channel_header_locator = (By.TAG_NAME, 'h4')
        _top_crashers_link_locator = (By.LINK_TEXT, 'Top Crashers')

        @property
        def product_version_label(self):
            return self.find_element(*self._release_channel_header_locator).text

        def click_top_crasher(self):
            self.find_element(*self._top_crashers_link_locator).click()
            from pages.crash_stats_top_crashers_page import CrashStatsTopCrashers
            return CrashStatsTopCrashers(self.selenium, self.page.base_url)
