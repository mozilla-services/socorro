$(document).ready(function() { 
    $("#signatureList").tablesorter({
        headers: { 0: { sorter: false }, 1: { sorter: false }}
      });
    $("#signatureList button").click(function(e){
        var button = $(this);
	var sig = button.attr('value');
        var graph = button.parents('tr').find('.sig-history-graph');
        var legend = button.parents('tr').find('.sig-history-legend');

        button.get(0).disabled = true;
        button.html("<img src='" + SocImg + "ajax-loader.gif' />");

	$.getJSON(SocAjax + encodeURI(sig) + SocAjaxStartEnd, function(data){
  	    graph.show();
	    button.remove();
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