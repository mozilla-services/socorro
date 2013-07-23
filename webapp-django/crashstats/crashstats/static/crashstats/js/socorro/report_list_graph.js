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

    function on_plothover(event, pos, item) {
        $("#x").text(pos.x.toFixed(2));
        $("#y").text(pos.y.toFixed(2));

        if (item) {
            if (previousPoint != item.dataIndex) {
                previousPoint = item.dataIndex;
                $("#graph-tooltip").remove();

                var x = item.datapoint[0].toFixed(2),
                  y = item.datapoint[1].toFixed(2);
                showTooltip(item.pageX, item.pageY, "Crash build date: " +
                            item.series.xaxis.ticks[previousPoint].label);
            }
        } else {
            $("#graph-tooltip").remove();
            previousPoint = null;
        }
    }

    function draw() {
        var $graph = $("#buildid-graph");
        $graph.width(1200);
        $graph.bind("plothover", on_plothover);

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
                  ticks: XAXIS_TICKS
            },
            yaxis: {
               min: 0
            },
            grid: { hoverable: true },
            legend: {
               show: true,
                  container: $("#graph-legend"),
                  noColumns: 4
            }
        };
        var datum = [{
           label: "Win",
           data: DATA.Win,
           color: "#27E"
        }, {
           label: "Mac",
           data: DATA.Mac,
           color: "#999"
        }, {
           label: "Lin",
           data: DATA.Lin,
           color: "#E50"
        }];

        var buildIdGraph = $.plot($graph, datum, opts);

        /* Hiding dates if they exceed a number > 20 to avoid overlap */
        if (buildIdGraph.getAxes().xaxis.ticks.length > 20) {
            $(".xAxis").hide();
        }

    }

    return {
       draw_idempotent: function() {
           if (!plot_drawn) {
               plot_drawn = true;
               draw();
           }
       }
    };

})();


$(document).ready(function() {
    var graph_tab = $('#report-list-nav a[href="#graph"]');
    var current_active_tab = $('#report-list-nav li.ui-tabs-active a');

    // To reasons to show the are if...
    // ...if the Graph tab is clicked
    graph_tab.click(function() {
        Plot.draw_idempotent();
    });
    /// ...or the Graph tab is already the active one
    if (current_active_tab.attr('href') === graph_tab.attr('href')) {
        Plot.draw_idempotent();
    }

});
