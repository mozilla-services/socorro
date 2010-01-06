$(document).ready(function() { 
  var graph = $('#sig-history-graph');
  var legend = $('#sig-history-legend');
  $.plot(graph,
	  [ 
		{ label: data.item1, data: data.ratio1 },
		{ label: data.item2, data: data.ratio2 },
		{ label: data.item3, data: data.ratio3 },
		{ label: data.item4, data: data.ratio4 },		
	  ],
	{
      xaxis:  { mode: 'time'},
      legend: {},
      series: {
        lines:  { show: true },
        points: { show: true },
	  },
	  grid:   { backgroundColor: "#ffffff" }
  });

  $("#click_by_version").bind("click", function(){
	showHideSelection("daily_search_version_form");
  });

  $("#click_by_os").bind("click", function(){
	showHideSelection("daily_search_os_form");
  });
});

function showHideSelection(id) {
	$("#daily_search_version_form").hide();
	$("#daily_search_os_form").hide();
	$("#"+id).show("fast");	
}

