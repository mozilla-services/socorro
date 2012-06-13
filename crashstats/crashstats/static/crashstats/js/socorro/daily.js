$(function() {
    var colours = ['#058DC7', '#ED561B', '#50B432', '#990099'],
        chartOpts = {
            xaxis: {
              mode: 'time',
              timeformat: "%b %d",
              minTickSize: [1, "day"],
            },
            yaxis: {
              min: 0,
            },
            series: {
                lines: { show: true },
                points: {
                    show: true,
                    radius: 1,
                },
                shadowSize: 0,
            },
            colors: colours,
            grid: {
                color: '#606060',
                backgroundColor: '#ffffff',
                borderColor: '#c0c0c0',
                borderWidth: 0
            },
            legend: {}
        };

    if (window.socGraphByReportType === true) {
        $('#adu-chart-controls button').click(function() {
            var currentData = [],
            noOfColumns = 8;
            for (var i=0; i < data.length; i++) {
                if ($('input[name=graph_data_' + i + ']').attr('checked')) {
                    currentData.push(data[i]);
                }
            }
            //if there are more then 8 items in the array we have to starting splittig into two rows
            if(currentData.length > 8) {
                noOfColumns = currentData.length / 2;
            }
            chartOpts.legend.noColumns = noOfColumns;
            chartOpts.legend.container = $("#adu-chart-legend");
            $.plot($("#adu-chart"), currentData, chartOpts);
            return false;
        }).trigger('click');
    } else {
        var chartData = [
            { data: data.ratio1 },
            { data: data.ratio2 },
            { data: data.ratio3 },
            { data: data.ratio4 }
        ];
        $.plot($("#adu-chart"), chartData, chartOpts);
    }

    $("#click_by_version").bind("click", function() {
        showHideDaily("daily_search_version_form");
    });

    $("#click_by_os").bind("click", function() {
        showHideDaily("daily_search_os_form");
    });

    $("#click_by_report_type").bind("click", function() {
        showHideDaily("daily_search_report_type_form");
    });

    $("#daily_search_version_form_products").change(function() {
        var url_form = $("#daily_search_version_form").attr('action'),
            product = $(this).find(":selected").val(),
            url = url_form + '?p=' + product;
        window.location = url;
    });

    $("#daily_search_os_form_products").change(function() {
        var url_form = $("#daily_search_os_form").attr('action'),
            product = $(this).find(":selected").val(),
            url = url_form + '?p=' + product;
        window.location = url;
    });

    for (i=0; i<=8; i++) {
        $("#version"+i).change(function() {
            var key = $(this).find(":selected").attr('key'),
                throttle_default = $(this).find(":selected").attr('throttle');
            $("#throttle"+key).val(throttle_default);
        });
    }

    $('h4').each(function() {
        $(this).css('color', colours.shift());
    });

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
    $("#daily_search_report_type_form").hide();
    $("#"+id).show("fast");
}

