$(function() {
    var aduChartContainer = $("#crashes-per-adi-graph"),
        colours = ['#6a3d9a', '#e31a1c', '#008800', '#1f78b4'];

    if (window.socGraphByReportType === false) {
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
                xax_start_at_min: true,
                interpolate: 'basic',
                area: false,
                legend: legend,
                legend_target: '#crashes-per-adi-legend'
            });

        } else {
            aduChartContainer.text('No results were found.');
        }
    }

    var windowHash = window.location.hash;
    if (windowHash === "#os_search") {
        showHideDaily("daily_search_os_form");
    } else {
        showHideDaily("daily_search_version_form");
    }

    $("#click_by_version").bind("click", function() {
        showHideDaily("daily_search_version_form");
    });

    $("#click_by_os").bind("click", function() {
        showHideDaily("daily_search_os_form");
    });

    $("#daily_search_version_form_products").change(function() {
        var url_form = $("#daily_search_version_form").attr('action'),
            product = $(this).find(":selected").val(),
            url = url_form + '?p=' + product + window.location.hash;
        window.location = url;
    });

    $("#daily_search_os_form_products").change(function() {
        var url_form = $("#daily_search_os_form").attr('action'),
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

function showHideDaily(id) {
    $("#daily_search_version_form").hide();
    $("#daily_search_os_form").hide();
    $("#"+id).show("fast");
}
