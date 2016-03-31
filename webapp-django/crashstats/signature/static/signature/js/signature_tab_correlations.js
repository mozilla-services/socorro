/*global SignatureReport: true, Accordion: true, socSortCorrelation:true */
/**
 * Tab for displaying correlations.
 * Does not have any panels.
 * Does not have any controls.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.CorrelationsTab = function (tabName) {

    var config  = {
        'panels': false,
        'dataDisplayType': 'table',
        'pagination': false,
    };

    SignatureReport.Tab.call(this, tabName, config);

};

SignatureReport.CorrelationsTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

SignatureReport.CorrelationsTab.prototype.onAjaxSuccess = function () {
    SignatureReport.Tab.prototype.onAjaxSuccess.apply(this, arguments);

    var wrapperElt = $('#correlations-wrapper');
    var baseUrl = wrapperElt.data('correlations-source');

    function urlMaker(product, version, os) {
        var url = baseUrl;
        url += '?product=' + product;
        url += '&version=' + version;
        url += '&platform=' + os;
        url += '&signature=' + SignatureReport.signature;
        return function makeUrl(types) {
            for (var i in types) {
                url += '&correlation_report_types=' + encodeURIComponent(types[i]);
            }
            return url;
        };
    }

    /**
     * Populates the panel specified by type.
     * @param {string} type - The correlation type
     * @param {object} data - The data to populate the panel with.
     */
    function populatePanel(container, type, data) {
        var contentContainer = $(
            '.content-pane[id^=' + type +'-correlation]',
            container
        );
        if (contentContainer.length !== 1) {
            throw new Error('Can\'t find the contentContainer ' + type);
        }
        var noData = $('<p />', {
            text: 'No correlation data found.',
        });

        if (data) {
            // first separate the data into individual 'rows'
            var dataRows = data.load.split(/\n/);
            var panelHeading = $('<h4 />', {
                text: data.reason,
            });

            // ensure there is at least one result and that the first item is
            // not an empty string.
            if (dataRows.length > 0 && dataRows[0] !== '') {

                var resultCountTxt = ' (' + dataRows.length + (dataRows.length > 1 ? ' results' : ' result') + ')';
                contentContainer.prev('h3').find('a').append(resultCountTxt);

                var table = $('<table />', {
                    class: 'data-table',
                });
                var thead = $('<thead />');
                var headerRow = $('<tr />');
                // a little work left to be done on the type header
                var headers = [
                    'All Crashes For Signature',
                    'All Crashes For OS',
                    type,
                ];

                $.each(headers, function (index, header) {
                    headerRow.append($('<th />', {
                        text: header,
                    }));
                });
                table.append(thead).append(headerRow);

                // loop through the lines and remove the vs. bits and split the
                // string into 3 'columns' per 'row'. Create the table rows and
                // attach them to the table.
                dataRows.forEach(function (row) {
                    var tableRow = $('<tr>');
                    row = row.replace(/\s+vs\.\s+/g, ' ');
                    var columns = [];
                    var numbers = row.match(/\d+% \([\d/]+\)/g);
                    numbers.forEach(function (number) {
                        columns.push(number);
                        row = row.replace(number, '');
                    });
                    // "the rest"
                    columns.push(row.trim());
                    columns.forEach(function (column) {
                        tableRow.append($('<td>', {
                            text: column,
                        }));
                    });
                    table.append(tableRow);
                });

                contentContainer.empty().append([panelHeading, table]);
                socSortCorrelation('.' + type + '_correlation');
            }
            // guard against empty records that sometimes gets returned.
            else if (dataRows.length === 1 && dataRows[0] === '') {
                // there seemed to be data but alas, it was an empty promise.
                contentContainer.empty().append(noData);
            }
        } else {
            contentContainer.empty().append(noData);
        }
    }

    // Load correlation data for various types.
    // @types CPU, Add-On, Module
    function loadCorrelationTabData(container, product, version, os, types) {
        var makeUrl = urlMaker(product, version, os);

        $.getJSON(makeUrl(types))
        .done(function (data) {
            for (var type in data) {
                populatePanel(container, type, data[type]);
            }
        })
        .fail(function (jqXHR, textStatus, errorThrown) {
            var msg = errorThrown;
            if (jqXHR.responseText !== '') {
                msg += ': ' + jqXHR.responseText;
            }
            for (var i in types) {
                $('.' + types[i] + '-correlation', container).html(msg);
            }
        });
    }

    $('.accordion').each(function () {
        (new Accordion(this)).init();
    });

    $('.correlation-combo').on('click', 'button.load-version-data', function () {
        var type = $(this).attr('name');
        var combo = $(this).parents('.correlation-combo');
        var product = combo.data('correlation-product');
        var version = combo.data('correlation-version');
        var os = combo.data('correlation-os');
        loadCorrelationTabData(
            combo,
            product,
            version,
            os,
            [type]
        );
    });

    var combos = $('.correlation-combo', wrapperElt).length;
    if (combos) {
        $('.correlation-combo', wrapperElt).each(function () {
            var combo = $(this);
            var product = combo.data('correlation-product');
            var version = combo.data('correlation-version');
            var os = combo.data('correlation-os');
            loadCorrelationTabData(
                combo,
                product,
                version,
                os,
                ['core-counts', 'interesting-addons', 'interesting-modules']
            );
        });

    }
};
