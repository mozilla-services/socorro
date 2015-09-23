/*global window, $, DATA, MG*/
/* This file a partial re-write from daily.js (which is deprecated) */

$(function() {
    'use strict';

    var COLORS = ['#6a3d9a', '#e31a1c', '#008800', '#1f78b4'];

    if (window.socGraphByReportType === false) {
        if (DATA.count) {
            // Format the graph data.
            var graphData = [];
            var legend = [];
            // This works because there are always
            // equally many labels as there are ratios
            // and their order is set.
            $.each(DATA.labels, function(i, label) {
                legend.push(label);
                graphData.push(
                    $.map(DATA.ratios[i], function(value) {
                        return {
                            date: new Date(value[0]),
                            ratio: value[1]
                        };
                    })
                );
            });

            // Draw the graph.
            MG.data_graphic({
                data: graphData,
                full_width: true,
                target: '#crashes-per-adi-graph',
                x_accessor: 'date',
                y_accessor: 'ratio',
                xax_start_at_min: true,
                utc_time: true,
                interpolate: 'basic',
                area: false,
                legend: legend,
                legend_target: '#crashes-per-adi-legend',
                show_secondary_x_label: false
            });

        } else {
            $('#crashes-per-adi-graph')
                .text('No results were found.');
        }
    }

    $('#daily_search_version_form_products').change(function() {
        var urlForm = $('#daily_search_version_form').attr('action'),
            product = $(this).find(':selected').val(),
            url = urlForm + '?p=' + product + window.location.hash;
        window.location = url;
    });

    $('#daily_search_os_form_products').change(function() {
        var urlForm = $('#daily_search_os_form').attr('action'),
            product = $(this).find(':selected').val(),
            url = urlForm + '?p=' + product + window.location.hash;
        window.location = url;
    });

    $('th.version').each(function() {
        $(this).css('color', COLORS.shift());
    });

    // To avoid having to set `title="Bla bla throttle something bla bla"`
    // on every th and td element that is about the throttle we just do
    // it here once with javascript
    $('th.throttle, td.throttle')
        .attr('title', $('table#crash_data').data('throttle-title'));

    $('.datepicker-daily input').datepicker({
        dateFormat: 'yy-mm-dd'
    });
});
