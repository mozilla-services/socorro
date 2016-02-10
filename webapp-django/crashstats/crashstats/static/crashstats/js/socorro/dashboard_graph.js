/*global window:true, $:true, socorro:true, MG: true */
$(function () {
    'use strict';

    var chartContainer = $('#homepage-graph-graph');
    var baseURL = chartContainer.data('frontpage-json-url') + '?';
    var currentHref = '';
    var dateRangeType = '';
    var dateRangeTypeValPattern = /(?!=)[a-zA-Z]{1,6}(?=:|$)/i;
    var durationPattern = /\d{1,2}(?=:|$)/;
    var durationValPattern = /(?!=)\d{1,6}(?=:|$)/;
    var colours = ['#6a3d9a', '#e31a1c', '#008800', '#1f78b4'];

    var setSelected = function (item, container) {
        $(container).find('a').removeClass('selected');
        item.addClass('selected');
    };

    var setSelectedByHash = function () {
        var hashString = window.location.hash.trim();
        if (hashString.length) {
            if (dateRangeTypeValPattern.exec(hashString) !== null) {
                $('#date-range-type a').each(function () {
                    if ($(this).attr('href').indexOf(dateRangeTypeValPattern.exec(hashString)) > -1) {
                        setSelected($(this), '#date-range-type');
                    }
                });
            }

            if (durationValPattern.exec(hashString) !== null) {
                $('#duration a').each(function () {
                    if ($(this).attr('href').indexOf(durationValPattern.exec(hashString)) > -1) {
                        setSelected($(this), '#duration');
                    }
                });
            }
        }
    };

    var manageHistory = function (key, value) {
        var newHashString = key + '=' + value;
        var currentKeyValue = '';

        var hashString = window.location.hash.trim();

        if (hashString.indexOf(key) === -1) {
            window.location.hash += hashString.length ? ':' + newHashString : newHashString;
        } else {
            if (key === 'date_range_type') {
                currentKeyValue = dateRangeTypeValPattern.exec(hashString);
                if (currentKeyValue !== value) {
                    newHashString = hashString.replace(currentKeyValue, value);
                }
            } else {
                currentKeyValue = durationValPattern.exec(hashString);
                if (currentKeyValue !== value) {
                    newHashString = hashString.replace(currentKeyValue, value);
                }
            }
            window.location.hash = newHashString;
        }
    };

    var buildAjaxURL = function () {
        var product = $('#products_select').val();
        var version = $('#product_version_select').val();
        var ajaxURL = baseURL;
        var hashString = window.location.hash;
        var dateRangeVal = dateRangeTypeValPattern.exec(hashString);

        var isDateRangeSet = hashString.indexOf('date_range_type');
        var isDurationSet = hashString.indexOf('duration');

        if (product.length) {
            ajaxURL += 'product=' + product;
        }

        if (version.length && version !== 'Current Versions') {
            ajaxURL += '&versions=' + version;
        }

        if (isDateRangeSet !== -1) {
            ajaxURL +=  '&date_range_type=' + dateRangeVal;
        }

        if (isDurationSet !== -1) {
            ajaxURL += '&duration=' + durationPattern.exec(hashString)[0];
        }

        return ajaxURL;
    };

    var setHeadersColors = function () {
        $('#release_channels h4')
        .each(function (index) {
            $(this).css('color', colours[index]);
        });
    };

    var drawGraph = function (ajaxURL) {
        socorro.ui.setLoader('#homepage-graph');
        $.getJSON(ajaxURL, function (data) {

            $('.loading').remove();

            setHeadersColors();

            if (data.count > 0) {

                // Format the graph data.
                var graphData = [];
                var legend = [];
                // In the returned data, the ratio keys are 1-indexed.
                for (var i = 1; i < data.labels.length + 1; i++) {
                    graphData.push(
                        $.map(data['ratio' + i], function (value) {
                            return {
                                'date': new Date(value[0]),
                                'ratio': value[1],
                            };
                        })
                    );

                    legend.push(data.labels[i - 1]);
                }

                // Draw the graph.
                MG.data_graphic({
                    data: graphData,
                    full_width: true,
                    target: '#homepage-graph-graph',
                    x_accessor: 'date',
                    y_accessor: 'ratio',
                    xax_start_at_min: true,
                    utc_time: true,
                    interpolate: 'basic',
                    area: false,
                    legend: legend,
                    legend_target: '#homepage-graph-legend',
                    show_secondary_x_label: false,
                });
            } else {
                chartContainer.empty().append('No Active Daily User crash data is available for this report.');
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            $('.loading').remove();
            chartContainer.empty().append('There was an error processing the request: Status: ' + textStatus + ' Error: ' + errorThrown);
        });
    };

    var handleClickEvent = function (anchor, container, key) {
        currentHref = anchor.attr('href');

        //set the clicked item to selected
        setSelected(anchor, container);

        dateRangeType = currentHref.substring(currentHref.indexOf('=') + 1);
        manageHistory(key, dateRangeType);
        drawGraph(buildAjaxURL());
    };

    var init = function () {
        setSelectedByHash();
        drawGraph(buildAjaxURL());
    };

    $('#date-range-type a').click(function (event) {
        event.preventDefault();
        handleClickEvent($(this), '#date-range-type', 'date_range_type');
    });

    $('#duration a').click(function (event) {
        event.preventDefault();
        handleClickEvent($(this), '#duration', 'duration');
    });

    // initialize and draw graph on DOM ready
    init();
});
