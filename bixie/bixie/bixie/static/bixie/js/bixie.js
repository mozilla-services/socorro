$(function() {
    var jsErrors = $('.jserror'),
          performanceGraph = $('#perf_graph');

    // First ensure we are on the report list page
    // and that we have errors to show.
    if(jsErrors.length > 0) {
        jsErrors.each(function() {
            $(this).click(function(event) {
                event.preventDefault();

                console.log($(this));

                $(this).children('span').toggleClass('collapse_icon');
                $(this).next('pre').toggleClass('expanded');
            });
        });
    }

    if(performanceGraph.length > 0) {
        var lineColors = ['#058DC7', '#ED561B', '#50B432', '#990099'],
        options = {
            colors: lineColors,
            series: {
                lines: {
                    lineWidth: 1
                }
            }
        };

        $.plot(performanceGraph, [getRandomData()], options);
    }
});
