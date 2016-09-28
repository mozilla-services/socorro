/* This file is deprecated in favor of crashes_per_user.js */

$(function() {
    var aduChartContainer = $("#crashes-per-adi-graph"),
        colours = ['#6a3d9a', '#e31a1c', '#008800', '#1f78b4'];

    var data = $('#mainbody').data('graph-data');

    if(data.count > 0) {

        // Format the graph data.
        var graphData = [];
        var legend = [];
        for (var i = 1; i < data.product_versions.length + 1; i++) {
            graphData.push(
                $.map(data['ratio' + i], function(value) {
                    return {
                        'date': new Date(value[0]),
                        'ratio': value[1]
                    };
                })
            );

            legend.push(data.labels[i - 1]);
        }

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
        aduChartContainer.text('No results were found.');
    }

    $("#daily_search_version_form_products").change(function() {
        var url_form = $("#daily_search_version_form").attr('action'),
            product = $(this).find(":selected").val(),
            url = url_form + '?p=' + product + window.location.hash;
        window.location = url;
    });

    for (i=0; i<=8; i++) {
        $("#version"+i).change(function() {
            var key = $(this).find(":selected").attr('key'),
                throttle_default = $(this).find(":selected").attr('throttle');
            $("#throttle"+key).val(throttle_default);
        });
    }

    $('th.version').each(function() {
        $(this).css('color', colours.shift());
    });

    //color by os table headers according to graph colors
    if($('th.os').length > 0) {
      $('th.os').each(function() {
        $(this).css('color', colours.shift());
      });
    }

    if ($(".datepicker-daily").length) {
        $(".datepicker-daily input").datepicker({
            dateFormat: "yy-mm-dd"
        });
    }
});
