/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/*jslint browser:true, regexp:false */
/*global window, $*/

$(document).ready(function () {
    //58% (2512/4354) vs.  36% (28055/78704) {20a82645-c095-46ed-80e3-08825760534b} (Microsoft .NET Framework Assistant, http://www.windowsclient.net/)
    var corrRegExp = /[^\d]*(\d*)%\s*\(.*vs[^\d]*(\d*)%\s*\([^/]*\/[^)]*\)\s*(.*)/,
        lineCache = {},
        percentageDifference,
        correlationItem,
        sortByCorrelation,
        firstLineOrEmptyString;

    percentageDifference = function (correlationLine) {
        var parts;
        if (lineCache[correlationLine]) {
            return lineCache[correlationLine];
        } else {
            parts = corrRegExp.exec(correlationLine);
            if (parts && 4 === parts.length) {
                lineCache[correlationLine] = parseInt(parts[1], 10) - parseInt(parts[2], 10);
                return parseInt(parts[1], 10) - parseInt(parts[2], 10);
            } else {
                return 0;
            }
        }
    };
    correlationItem = function (correlationLine) {
        var parts = corrRegExp.exec(correlationLine);
        if (parts && 4 === parts.length) {
            return parts[3];
        } else {
            return '';
        }
    };
    sortByCorrelation = function (a, b) {
        var aDiff = percentageDifference(a),
            bDiff = percentageDifference(b);
        if (aDiff < bDiff) {
            return 1;
        } else if (aDiff > bDiff) {
            return -1;
        } else {
            return 0;
        }
    };

    /**
     * Sorts the correlation reports and updates
     * the HTML.
     * @param string jQuery compatible selector for overall element
     * @return void Updates the dom as a side effect
     */
    window.socSortCorrelation = function (jQueryId) {
        // jQueryId = '#cpu_correlation'
        $(jQueryId + ' .correlation pre').each(function () {
            var lines = $(this).text().split('\n');
            lines.sort(sortByCorrelation);
            $(this).text(lines.join('\n'));
        });
    };

    firstLineOrEmptyString = function (lines) {
        if (typeof lines !== 'string') {
            return '';
        }
        var parts = lines.split('\n');
        if (parts.length > 0) {
            return parts[0];
        }
    };

    /**
     * Determines which of the correlation reports in the DOM
     * has the highest correlation. Items must already be sorted
     * via socSortCorrelation
     * @param string jQuery compatible selector for overall element
     * @return string Formatted line for the highest correlation. Will
     *                start with UNKNOWN if none is available.
     */
    window.socDetermineHighestCorrelation = function (jQueryId) {
        var cpuLine    = firstLineOrEmptyString($('.cpus .correlation pre', jQueryId).text()),
            addonLine  = firstLineOrEmptyString($('.addons .correlation pre', jQueryId).text()),
            moduleLine = firstLineOrEmptyString($('.modules .correlation pre', jQueryId).text()),
            cpu = percentageDifference(cpuLine),
            addon = percentageDifference(addonLine),
            module = percentageDifference(moduleLine);

        if (cpu === 0 && addon === 0 && module === 0) {
            return 'UNKNOWN: No Data';
        } else if (cpu >= addon &&
            cpu >= module) {
            return 'CPU: ' + correlationItem(cpuLine);
        } else if (addon >= cpu &&
                   addon >= module) {
            return 'ADD-ON: ' + correlationItem(addonLine);
        } else {
            return 'MODULE: ' + correlationItem(moduleLine);
        }
    };
});
