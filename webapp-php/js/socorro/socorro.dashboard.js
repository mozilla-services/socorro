/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$(function() {
	/* striped tables */
	var zebra = function(table) {
	    table.find("tbody tr:odd").addClass("odd");
	}, 
	toStripe = false,
    ajaxLoader = new Image(),
    dashTables = $(".sig-dashboard-tbl", "#sig-dashboard-body");
    
    ajaxLoader.src = "../img/icons/ajax-loader.gif";
    ajaxLoader.setAttribute("id", "dash-loader");
    $("#sig-dashboard-body").append(ajaxLoader);
	
	$.getJSON(json_path, function(data) {
		var socorroDashBoardData = data,
		percentageByOsHtml = "",
		uptimeRangeHtml = "",
		productVersionsHtml = "",
		architectureHtml = "",
		processTypeHtml = "",
		flashVersionHtml = "";
        
        if(!$.isArray(socorroDashBoardData)) {
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
