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
  	grid: {
  		color: '#606060',
  		backgroundColor: '#ffffff',
  		borderColor: '#c0c0c0',
  		borderWidth: 0
  		},  	
    };
  if (window.socGraphByReportType === true) {
    //$.plot($("#adu-chart"), data, chartOpts);

    $('#adu-chart-controls button').click(function() {
      var currentData = [];
      for (var i=0; i < data.length; i++) {
	if ($('input[name=graph_data_' + i + ']').attr('checked')) {
          currentData.push(data[i]);
        }
      }
      $.plot($("#adu-chart"), currentData, chartOpts);
      return false;
    }).trigger('click');
  } else {
    chartOpts['colors'] = [ '#058DC7', '#ED561B', '#50B432', '#990099'];
    chartOpts['legend'] = {};
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
        if (window.console) { console.error(err); }
    }
  }

  $("#click_by_version").bind("click", function(){
    showHideDaily("daily_search_version_form");
  });

  $("#click_by_os").bind("click", function(){
    showHideDaily("daily_search_os_form");
  });

  $("#click_by_report_type").bind("click", function(){
    showHideDaily("daily_search_report_type_form");
  });

});

function showHideDaily(id) {
	$("#daily_search_version_form").hide();
	$("#daily_search_os_form").hide();
	$("#daily_search_report_type_form").hide();
	$("#"+id).show("fast");	
}
