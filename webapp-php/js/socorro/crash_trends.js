$(function() {
    var graph,
    drawCrashTrends = function() {
        var dates = ["20110905", "20110906", "20110907", "20110908", "20110909", "20110910", "20110911"],
        i = 0,
        options = {
            legend: {
                noColumns: 7,
                container: "#graph_legend"
            },
            xaxis: {
                tickFormatter: function(val, axis) {
                    val = dates[i];
                    i++;
                    return val;
                }
            }
        },
        graphData = $.getJSON("/webservice/nightlytrends", function(data) {
            graph = $.plot("#nightly_crash_trends_graph", data.nightlyCrashes, options);    
        });
    };
    
    drawCrashTrends();
});
