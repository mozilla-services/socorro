/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/*jslint browser:true, jQuery:false */
/*global window, $, BugLinks */

$(document).ready(function () {
    var perosTbl = $('#peros-tbl');

    $('#signature-list').tablesorter({
        sortInitialOrder: 'desc',
        headers: {
            0: { sorter: 'digit' },
            1: { sorter: false },
            5: { sorter: 'digit' },
            6: { sorter: 'digit' },
            7: { sorter: 'digit' },
            8: { sorter: 'digit' },
            9: { sorter: 'date' },  // First Appearance
            11: { sorter: false },  // Bugzilla IDs
        },
    });

    perosTbl.tablesorter({
        headers: {
            0: { sorter: 'digit' },
            1: { sorter: false },
            4: { sorter: 'text' },
            5: { sorter: 'digit' },
            6: { sorter: 'digit' },
            7: { sorter: 'digit' },
        },
    });

    $('#signature-list tr, #peros-tbl tr').each(function() {
        $.data(this, 'graphable', true);
    });

    // Enhance bug links.
    BugLinks.enhanceExpanded();
});
