$(function() {
	/* striped tables */
	var zebra = function(table) {
	    table.find("tbody tr:odd").addClass("odd");
	}, 
	toStripe = false;
	
	$.getJSON(json_path, function(data) {
		var socorroDashBoardData = data,
		percentageByOsHtml = "",
		uptimeRangeHtml = "",
		productVersionsHtml = "";
		
		percentageByOsHtml = Mustache.to_html(percentageByOsTmpl, socorroDashBoardData);
		uptimeRangeHtml = Mustache.to_html(uptimeRangeTmpl, socorroDashBoardData);
		productVersionsHtml = Mustache.to_html(productVersionsTmpl, socorroDashBoardData);
		
		$(percentageByOsHtml).appendTo("#percentageByOsBody");
		$(uptimeRangeHtml).appendTo("#uptimeRangeBody");
		$(productVersionsHtml).appendTo("#productVersionsBody");
		
		/* Rows are dynamically added ofter DOM ready so have to move striping code here */
		toStripe = !!$(".zebra").length;
	
		if(toStripe) {
		    $(".zebra").each(function() {
		        zebra($(this));
		    });
		}
	});
});
