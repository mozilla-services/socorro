/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/*jslint browser:true, regexp:false, plusplus:false, jQuery:false */
/*global window, $, BugLinks */

var Correlations = (function() {
    // This DOM element has all the data attributes we need to transfer
    // from the rendering into this JavaScript.
    var $container = $('#mainbody');
    var product = $container.data('product');
    var version = $container.data('version');
    var channel = 'release';
    if (version.indexOf('b') != -1) {
      channel = 'beta';
    } else if (version.indexOf('a1') != -1) {
      channel = 'aurora';
    } else if (version.indexOf('a2') != -1) {
      channel = 'nightly';
    }
    var loadingImage = $('<img/>')
        .attr('src', $container.data('loading-img'))
        .attr('width', 16)
        .attr('height', 17);

    function expandCorrelation($element) {
        var row = $element.parents('tr');

        $('.correlation-cell .top span', row).empty().append(loadingImage);
        var signature = row.find('.signature').attr('title');

        var contentElt = $('.correlation-cell div div.complete pre', row);

        window.correlations.getCorrelations(signature, channel, product)
        .then(function (results) {
            var content = results;
            if (Array.isArray(results)) {
                content = results.join('\n');
            }
            $('.correlation-cell .top span', row).html('');
            $('.correlation-cell div div.complete', row).show();
            $element.text('Hide');
            contentElt.empty().append(content);
        });

        return false;
    }

    function contractCorrelation($element) {
        var row = $element.parents('tr');
        $('.correlation-cell div div.complete', row).hide();
        $element.text('Show');
        return false;
    }

    return {
        init: function() {
            // set up an expander clicker
            $('.correlation-cell a.correlation-toggler').click(function() {
                var $element = $(this);
                var was_clicked = $element.hasClass('__clicked');
                // close all expanded
                $('.__clicked').each(function() {
                    contractCorrelation($(this).removeClass('__clicked'));
                });
                if (!was_clicked) {
                    expandCorrelation($element.addClass('__clicked'));
                }
                return false;
            });
        },
    };
})();

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
            12: { sorter: false },  // Correlation
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

    /* Initialize things */
    Correlations.init();
});
