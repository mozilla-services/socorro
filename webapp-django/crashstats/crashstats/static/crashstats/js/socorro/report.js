/*jslint browser:true, regexp:false */
/*global window, $, socSortCorrelation, SocReport */

var SignatureCorrelations = (function() {
    var container = $('#mainbody');
    return {
        showSignatureCorrelationsTab: function() {
            // If that number is -1, we don't know if there are correlations.
            // Find out, by ajax, and if the count is >0, then make the
            // "Correlations" tab visible.
            if (container.data('total-correlations') < 0) {
                $.getJSON(container.data('correlations-signature-count-url'))
                .then(function(response) {
                    if (response.count) {
                        $('li.correlations').show();
                    }
                })
                .fail(function() {
                    console.warn('Failed to see if there are correlations');
                    console.error.apply(console, arguments);
                });
            }
        }
    };
})();


$(document).ready(function () {
    $('#report-index').tabs({
        selected: 0,
        activate: function(event, ui) {
            Analytics.trackTabSwitch('report_index', ui.newPanel.attr('id'));
        }
    });

    var container = $('#mainbody');
    var correlationsURL = container.data('correlations-url');
    var correlationsParams = {
        product: container.data('product'),
        version: container.data('version'),
        platform: container.data('platform'),
        signature: container.data('signature'),
    };

    var loadCorrelationTypes = function(types) {
        $.map(types, function(type) {
            correlationsParams.correlation_report_types = type;
            $.getJSON(correlationsURL, correlationsParams, function(response) {
                var data = response[type];
                var group = $('#' + type + '_correlation');
                if (group.length !== 1) {
                    console.warn('There is not exactly 1 "#' + type + '_correlation"');
                } else {
                    group
                    .empty()
                    .append(
                        $('<h3>').text(data.reason)
                    );
                    if (data.load) {
                        group.append(
                            $('<pre>').text(data.load)
                        );
                    } else {
                        group.append(
                            $('<i>').text('none')
                        );
                    }
                    socSortCorrelation('#' + type + '_correlation');
                }
            });
        });
    };

    var loadDefaultCorrelationTypes = function() {
        loadCorrelationTypes([
            'core-counts',
            'interesting-addons',
            'interesting-modules',
        ]);
    };

    var loadCorrelations = true;
    $('a[href="#correlation"]').on('click', function () {
        if (!loadCorrelations) {
            return;
        }
        loadCorrelations = false;
        loadDefaultCorrelationTypes();
    });

    $('button.load-version-data').on('click', function () {
        var type = $(this).attr('name');
        loadCorrelationTypes([type]);
    });

    $('a[href="#allthreads"]').on('click', function () {
        var element = $(this);
        $('#allthreads').toggle(400);
        if (element.text() === element.data('show')) {
            element.text(element.data('hide'));
            return true;
        } else {
            element.text(element.data('show'));
            location.hash = 'frames';
            return false;
        }
    });

    // if the page is loaded with #allthreads, then pretend we immediately
    // click the toggle switch.
    if (location.hash === '#allthreads') {
        $('a[href="#allthreads"]').click();
    } else if (location.hash === '#correlation') {
        $('a[href="#correlation"]').click();
    }

    var tbls = $("#frames").find("table");
    var addExpand = function(sigColumn) {
        $(sigColumn).append(' <a class="expand" href="#">[Expand]</a>');
        $('.expand').click(function(event) {
            event.preventDefault();
            // swap cell title into cell text for each cell in this column
            $("td:nth-child(3)", $(this).parents('tbody')).each(function () {
                $(this).text($(this).attr('title')).removeAttr('title');
            });
            $(this).remove();
        });
    };

    // collect all tables inside the div with id frames
    tbls.each(function() {
        var isExpandAdded = false,
        cells = $(this).find("tbody tr td:nth-child(3)");

        // Loop through each 3rd cell of each row in the current table and if
        // any cell's title atribute is not of the same length as the text
        // content, we need to add the expand link to the table.
        // There is a second check to ensure that the expand link has not been added already.
        // This avoids adding multiple calls to addExpand which will add multiple links to the
        // same header.
        cells.each(function() {
            if(($(this).attr("title").length !== $(this).text().length) && (!isExpandAdded)) {
                addExpand($(this).parents("tbody").find("th.signature-column"));
                isExpandAdded = true;
            }
        });
    });

    $('#modules-list').tablesorter({sortList: [[1, 0]], headers: {1: {sorter : 'digit'}}});

    // Decide whether to show the Correlations tab if this product,
    // version, platform and signature has correlations.
    SignatureCorrelations.showSignatureCorrelationsTab();

    // Enhance bug links.
    BugLinks.enhance();
});
