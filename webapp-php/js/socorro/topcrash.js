$(document).ready(function() { 
    $("#signatureList").tablesorter({
        headers: { 0: { sorter: false }, 1: { sorter: false }}
      });
    $("#signatureList").click(function(e){
	
	window.e = e;
	var sig = $(e.originalEvent.target).parents('tr').find('.signature').text();
        var graph = $(e.originalEvent.target).parents('tr').find('.sig-history-graph');
        var legend = $(e.originalEvent.target).parents('tr').find('.sig-history-legend');
	graph.show();
        graph.text("Loading data for " + sig);

	$.getJSON(SocAjax + encodeURI(sig), function(data){
	    window.data = data;
            $.plot(graph,
	       [{ data: data.counts,   label: 'Count',  yaxis: 1},
                { data: data.percents, label: 'Percent',   yaxis: 2}],
	       {//options
	           xaxis: {mode: 'time'},
	           legend: {container: legend, margin: 0, labelBoxBorderColor: '#FFF'},
                   series: {
                       lines: { show: true },
                       points: { show: true },

                   },
               });
        });
    });
});