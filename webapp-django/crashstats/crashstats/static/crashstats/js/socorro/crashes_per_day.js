/*global window, $, MG*/

$(function() {
    'use strict';

    var COLORS = ['#6a3d9a', '#e31a1c', '#008800', '#1f78b4'];

    var data = $('#mainbody').data('graph-data');

    if (data.count) {
        // Format the graph data.
        var graphData = [];
        var legend = [];
        // This works because there are always
        // equally many labels as there are ratios
        // and their order is set.
        $.each(data.labels, function(i, label) {
            legend.push(label);
            graphData.push(
                $.map(data.ratios[i], function(value) {
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
            axes_not_compact: true,
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
