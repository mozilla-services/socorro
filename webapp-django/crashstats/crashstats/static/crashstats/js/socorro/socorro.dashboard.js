/* jshint jquery:true */
/* globals json_path:false, Mustache: false, percentageByOsTmpl:false,
   uptimeRangeTmpl: false, productVersionsTmpl:false, architectureTmpl:false,
   processTypeTmpl:false, flashVersionTmpl:false, distinctInstallTmpl:false,
   exploitabilityScoreTmpl:false */
$(function() {
    "use strict";
    var ajaxLoader = new Image(),
    dashTables = $(".sig-dashboard-tbl", "#sig-dashboard-body");

    ajaxLoader.src = "/static/img/icons/ajax-loader.gif";
    ajaxLoader.setAttribute("id", "dash-loader");
    $("#sig-dashboard-body").append(ajaxLoader);

    // Show and hide table contents on caption click.
    $("#sig-dashboard-body").on("click", "caption", function(event) {
        event.preventDefault();
        $(this).parent("table").toggleClass("initially-hidden");
    });

    $.getJSON(json_path, function(data) {
        var socorroDashBoardData = data,
        empty_signature_summary = true,
        percentageByOsHtml = "",
        uptimeRangeHtml = "",
        productVersionsHtml = "",
        architectureHtml = "",
        processTypeHtml = "",
        flashVersionHtml = "",
        distinctInstallHtml = "",
        exploitabilityScoreHtml = "",
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
            distinctInstallHtml = Mustache.to_html(distinctInstallTmpl, socorroDashBoardData);
            exploitabilityScoreHtml = Mustache.to_html(exploitabilityScoreTmpl, socorroDashBoardData);

            $(percentageByOsHtml).appendTo("#percentageByOsBody");
            $(uptimeRangeHtml).appendTo("#uptimeRangeBody");
            $(productVersionsHtml).appendTo("#productVersionsBody");
            $(architectureHtml).appendTo("#architectureBody");
            $(processTypeHtml).appendTo("#processTypeBody");
            $(flashVersionHtml).appendTo("#flashVersionBody");
            $(distinctInstallHtml).appendTo("#distinctInstallBody");
            $(exploitabilityScoreHtml).appendTo("#exploitabilityScoreBody");

             dashTables.show();
        } else {
            $("#sig-dashboard-body").append("<p>No summary data found for period.</p>");
        }
        /* remove the loading animation */
        $("#dash-loader").remove();
    });
});
