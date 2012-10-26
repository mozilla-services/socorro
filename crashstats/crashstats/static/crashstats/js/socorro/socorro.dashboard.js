$(function() {
    /* striped tables */
    var zebra = function(table) {
        table.find("tbody tr:odd").addClass("odd");
    },
    toStripe = false,
    ajaxLoader = new Image(),
    dashTables = $(".sig-dashboard-tbl", "#sig-dashboard-body");

    ajaxLoader.src = "/static/img/icons/ajax-loader.gif";
    ajaxLoader.setAttribute("id", "dash-loader");
    $("#sig-dashboard-body").append(ajaxLoader);

    $.getJSON(json_path, function(data) {
        var socorroDashBoardData = data,
        empty_signature_summary = true,
        percentageByOsHtml = "",
        uptimeRangeHtml = "",
        productVersionsHtml = "",
        architectureHtml = "",
        processTypeHtml = "",
        flashVersionHtml = "",
        report_type = "";

        // Check whether any of the report types has data. If
        // at least one has data, set empty_signature_summary
        // to false.
        for(report_type in data) {
            if(data[report_type].length) {
                empty_signature_summary = false;
            }
        }

        if(!empty_signature_summary) {
            percentageByOsHtml = Mustache.to_html(percentageByOsTmpl, socorroDashBoardData);
            uptimeRangeHtml = Mustache.to_html(uptimeRangeTmpl, socorroDashBoardData);
            productVersionsHtml = Mustache.to_html(productVersionsTmpl, socorroDashBoardData);
            architectureHtml = Mustache.to_html(architectureTmpl, socorroDashBoardData);
            processTypeHtml = Mustache.to_html(processTypeTmpl, socorroDashBoardData);
            flashVersionHtml = Mustache.to_html(flashVersionTmpl, socorroDashBoardData);

            $(percentageByOsHtml).appendTo("#percentageByOsBody");
            $(uptimeRangeHtml).appendTo("#uptimeRangeBody");
            $(productVersionsHtml).appendTo("#productVersionsBody");
            $(architectureHtml).appendTo("#architectureBody");
            $(processTypeHtml).appendTo("#processTypeBody");
            $(flashVersionHtml).appendTo("#flashVersionBody");

             dashTables.show();

             /* Rows are dynamically added ofter DOM ready so have to move striping code here */
            toStripe = !!$(".zebra").length;

            if(toStripe) {
                $(".zebra").each(function() {
                    zebra($(this));
                });
            }
        } else {
            $("#sig-dashboard-body").append("<p>No summary data found for period.</p>");
        }
        /* remove the loading animation */
        $("#dash-loader").remove();
    });
});
