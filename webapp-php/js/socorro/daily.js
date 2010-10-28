$(document).ready(function() { 
  var chartOpts = {
  	xaxis: {
  		mode: 'time',
  		timeformat: "%b %d",
  		minTickSize: [1, "day"],
  		autoscaleMargin: .1
  		},
  	yaxis: {
  		autoscaleMargin: .05
  		},
  	series: {
  		lines: { show: true },
  		points: { show: false },
  		shadowSize: 0,
  		},
  	colors: [ '#058DC7', '#ED561B', '#50B432', '#990099'],
  	grid: {
  		color: '#606060',
  		backgroundColor: '#ffffff',
  		borderColor: '#c0c0c0',
  		borderWidth: 0
  		},
  	legend: {
  	}
  };

  try {
      var chartData = [
    	{ label: data.item1, data: data.ratio1 },
    	{ label: data.item2, data: data.ratio2 },
    	{ label: data.item3, data: data.ratio3 },
    	{ label: data.item4, data: data.ratio4 }
      ];
      
      $(document).ready(function() {
          $.plot($("#adu-chart"), chartData, chartOpts);
      });

  } catch(err) {

  }

  $("#click_top_crashers").bind("click", function(){
	showHideTop("top_crashers");
  });

  $("#click_top_changers").bind("click", function(){
	showHideTop("top_changers");
  });
  
  $("#click_by_version").bind("click", function(){
    showHideDaily("daily_search_version_form");
  });

  $("#click_by_os").bind("click", function(){
    showHideDaily("daily_search_os_form");
  });

  $("#daily_search_version_form_products").change(function(){
    var url_form = $("#daily_search_version_form").attr('action');
    var product = $(this).find(":selected").val();
    var url = url_form + '?p=' + product;
    window.location = url;
  });
  
  $("#daily_search_os_form_products").change(function(){
    var url_form = $("#daily_search_os_form").attr('action');
    var product = $(this).find(":selected").val();
    var url = url_form + '?p=' + product;
    window.location = url;
  });

  for (i=0; i<=4; i++){
    $("#version"+i).change(function(){
      var key = $(this).find(":selected").attr('key');
      var throttle_default = $(this).find(":selected").attr('throttle');
      $("#throttle"+key).val(throttle_default);
    });
  }
  
});

function showHideTop(id) {
	$("#top_crashers").hide();
	$("#top_changers").hide();
	$("#"+id).show("fast");	
}

function showHideDaily(id) {
	$("#daily_search_version_form").hide();
	$("#daily_search_os_form").hide();
	$("#"+id).show("fast");	
}
