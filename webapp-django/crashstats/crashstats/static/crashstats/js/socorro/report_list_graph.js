/*global DATA XAXIS_TICKS */

var Plot = (function() {

    var previousPoint = null;
    var plot_drawn = false;

    function showTooltip(x, y, contents) {
        $('<div id="graph-tooltip">')
          .text(contents)
            .css({
               top: y + 5,
                left: x + 5
            }).appendTo("body").fadeIn(200);
    }

    function onPlotHover(event, pos, item) {
        $("#x").text(pos.x.toFixed(2));
        $("#y").text(pos.y.toFixed(2));

        if (item) {
            if (previousPoint != item.dataIndex) {
                previousPoint = item.dataIndex;
                $("#graph-tooltip").remove();

                var x = item.datapoint[0].toFixed(2);
                var y = item.datapoint[1].toFixed(2);
                showTooltip(item.pageX, item.pageY, "Crash build date: " +
                            item.series.xaxis.ticks[previousPoint].label);
            }
        } else {
            $("#graph-tooltip").remove();
            previousPoint = null;
        }
    }

    function draw(data) {
        var $graph = $("#buildid-graph");
        $graph.width(1200);
        $graph.bind("plothover", onPlotHover);

        var opts = { // options
            // Crashes by development builds Frequency over build day
            lines: {
               show: true
            },
            points: {
               show: true
            },
            xaxis: {
               labelWidth: 55,
               ticks: data.xaxis_ticks
            },
            yaxis: {
               min: 0
            },
            grid: {
               hoverable: true
            },
            legend: {
               show: true,
               container: $("#graph-legend"),
               noColumns: 4
            }
        };
        var datum = [{
           label: "Win",
           data: data.Win,
           color: "#27E"
        }, {
           label: "Mac",
           data: data.Mac,
           color: "#999"
        }, {
           label: "Lin",
           data: data.Lin,
           color: "#E50"
        }];

        var buildIdGraph = $.plot($graph, datum, opts);

        /* Hiding dates if they exceed a number > 20 to avoid overlap */
        if (buildIdGraph.getAxes().xaxis.ticks.length > 20) {
            $(".xAxis").hide();
        }

    }

    return {
       drawIdempotent: function(data) {
           if (!plot_drawn) {
               plot_drawn = true;
               draw(data);
           }
       }
    };

})();


var Graph = (function() {
    var loaded = null;

    return {
       activate: function() {
           if (loaded) return;
           var deferred = $.Deferred();
           var $panel = $('#graph');
           var url = $panel.data('partial-url');
           var qs = location.href.split('?')[1];
           url += '?' + qs;
           var req = $.ajax({
               url: url
           });
           req.done(function(response) {
               $('.loading-placeholder', $panel).hide();
               $('.inner', $panel).html(response);
               Plot.drawIdempotent(DATA);
               deferred.resolve();
           });
           req.fail(function(data, textStatus, errorThrown) {
               deferred.reject(data, textStatus, errorThrown);
           });
           loaded = true;
           return deferred.promise();
       }
    };
})();


Panels.register('graph', function() {
    return Graph.activate();
});
