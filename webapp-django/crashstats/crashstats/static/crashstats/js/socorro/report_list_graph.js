/* global $ */

// Base D3 code by @bsmedberg
// With additional code, tweaks and UI
// goodness by @espressive
var Plot = (function() {

    var buildIDParser = d3.time.format.utc("%Y%m%d%H%M%S").parse;
    function buildIDToDate(bid) {
        return buildIDParser(bid);
    }

    function Dimensions(o) {
        if (!(this instanceof Dimensions)) {
            throw Error("Use new Dimensions()");
        }
        if (o !== undefined) {
            for (var k in o) {
            this[k] = o[k];
            }
        }
    }

    Dimensions.prototype.radius = function() {
      return Math.min(this.width, this.height) / 2;
    };

    Dimensions.prototype.totalWidth = function() {
      return this.width + this.marginLeft + this.marginRight;
    };

    Dimensions.prototype.totalHeight = function() {
      return this.height + this.marginTop + this.marginBottom;
    };

    Dimensions.prototype.transformUpperLeft = function(e) {
      e.attr("transform", "translate(" + this.marginLeft + "," + this.marginTop + ")");
    };

    Dimensions.prototype.transformCenter = function(e) {
      e.attr("transform", "translate(" + (this.marginLeft + this.width / 2) + "," +
             (this.marginTop + this.height / 2) + ")");
    };

    Dimensions.prototype.setupSVG = function(e) {
      e.attr({
        width: this.totalWidth(),
        height: this.totalHeight()
      });
    };

    /**
     * Draws the x grid lines
     */
    function make_x_axis(x) {
        return d3.svg.axis()
            .scale(x)
            .orient('bottom')
            .ticks(4);
    }

    /**
     * Draws the y grid lines
     */
    function make_y_axis(y) {
        return d3.svg.axis()
            .scale(y)
            .orient('left')
            .ticks(4);
    }

    /**
     * Draws the ADU graph
     * @param {object} data - The JSON data (data.hits)
     * @param {object} container - The graph container as jQuery object
     */
    function drawGraph(data, container) {

        var finalData = d3.nest()
            .key(function(d) {
                return d.buildid;
            })
            .rollup(function(dlist) {
                var r = {
                    adu_count: d3.sum(dlist, function(d) {
                        return d.adu_count;
                    }),
                    crash_count: d3.sum(dlist, function(d) {
                        return d.crash_count;
                    })
                };

                if (r.adu_count) {
                    r.ratio = r.crash_count / r.adu_count;
                }
                return r;
            })
            .sortKeys()
            .entries(data)
            .filter(function(d) {
                return d.values.ratio !== undefined;
            });

        var adus = finalData.map(function(d) {
            return d.values.adu_count;
        });
        adus.sort(d3.ascending);

        var cutoff = d3.quantile(adus, 0.2);

        finalData = finalData.filter(function(d) {
            return d.values.adu_count > cutoff;
        });

        var dims = new Dimensions({
            width: 800,
            height: 250,
            marginTop: 25,
            marginLeft: 95,
            marginRight: 10,
            marginBottom: 50
        });

        // setup the x and y axis scales
        var minx = buildIDToDate(finalData[0].key);
        var maxx = buildIDToDate(finalData[finalData.length -1].key);
        var x = d3.time.scale()
            .range([0, dims.width])
            .domain([minx, maxx]);
        var xaxis = d3.svg.axis()
            .scale(x)
            .orient('bottom');

        var maxy = d3.max(finalData, function(d) {
            return d.values.ratio;
        });
        var y = d3.scale.linear()
            .rangeRound([10, dims.height])
            .domain([maxy, 0]);
        var yaxis = d3.svg.axis()
            .scale(y)
            .ticks(4)
            .orient('left');

        var svg = d3.select('svg', container)
            .call(function(d) {
                dims.setupSVG(d);
            })
            .append('g')
            .call(function(d) {
                dims.transformUpperLeft(d);
            });

        svg.append('text')
            .text('Hover over a point below to see the details for each data point.')
            .attr('x', 0)
            .attr('y', -5);

        svg.append('g')
           .attr('class', 'grid')
           .attr('transform', 'translate(0,' + dims.height + ')')
           .call(make_x_axis(x)
                .tickSize(-dims.height + 10, 0, 0)
                .tickFormat('')
            );

        svg.append('g')
           .attr('class', 'grid')
           .call(make_y_axis(y)
                .tickSize(-dims.width, 0, 0)
                .tickFormat('')
            );

        svg.append('g')
           .attr('class', 'x axis')
           .attr('transform', 'translate(0,' + dims.height + ')')
           .call(xaxis);

        svg.append('text')
           .text('Build Date')
           .attr('x', dims.width / 2)
           .attr('y', dims.height + 32)
           .attr('dominant-baseline', 'hanging');

        svg.append('g')
           .attr('class', 'y axis')
           .call(yaxis);

        svg.append('text')
           .text('Crashes/ADU')
           .attr('transform', 'translate(' + (-dims.marginLeft + 5) + ',' + (dims.height / 2) + ') rotate(-90)')
           .attr('text-anchor', 'middle')
           .attr('dominant-baseline', 'hanging');


        var tooltip = d3.select('.adubysig').append('div')
            .attr('class', 'tooltip')
            .style('top', 0)
            .style('left', 0);

        var points = svg.selectAll('.point')
            .data(finalData);


        var entered = points.enter()
            .append('circle')
            .attr('class', 'point main')
            .attr('fill', '#406a80')
            .attr('cx', function(d) {
                return x(buildIDToDate(d.key));
            })
            .attr('cy', function(d) {
                return y(d.values.ratio);
            })
            .attr('r', 6)
            .style('opacity', 0)
            .on('mouseenter', function(d) {
                var pos = d3.mouse(this);

                var tooltipContentContainer = $('<ul />', {
                    class: 'tooltip-content'
                });

                var buildId = $('<li />', {
                    text: 'BuildID: ' + d.key
                });

                var aduCount = $('<li />', {
                    text: 'ADU Count: ' + d.values.adu_count
                });

                var crashCount = $('<li />', {
                    text: 'Crash Count: ' + d.values.crash_count
                });

                tooltipContentContainer.append([buildId, aduCount, crashCount]);

                var calcTop = pos[1] + 60;
                var calcLeft = pos[0] - 60;

                tooltip.style('display', 'block')
                    .style('top', calcTop + 'px')
                    .style('left', calcLeft > 100 ?
                            calcLeft + 'px' :
                            (calcLeft + 200) + 'px')
                    .html(tooltipContentContainer.html())
                    .transition()
                    .delay(300)
                    .duration(500)
                    .style('opacity', 1);
            })
            .on('mouseout', function(d) {
                tooltip.transition()
                    .style('opacity', 0);
            });

        entered.transition()
            .delay(400)
            .duration(600)
            .style('opacity', 1);
    }

    /**
     * Adds a select drop-down to the graph tab, so users
     * can toggle between different channels.
     * param {object} dataSet - Object containing all data attribute values
     */
    function addChannelSelector(dataSet) {
        var channels = dataSet.fallback.split(',');
        var channelsLength = channels.length;

        var label = $('<label />', {
            for: 'channel-select',
            text: 'Release Channel'
        });
        var select = $('<select />', {
            id: 'channel-select'
        });

        $(channels).each(function(i, channel) {
            var option = $('<option />', {
                value: channel,
                text: channel,
            });

            // set nightly release channel as the default selected
            if (channel === 'nightly') {
                option.attr('selected', 'selected');
            }

            select.append(option);
        });

        var heading = $('#adubysig-heading');
        // strick the select and it's label just after the heading
        heading.after(label, select);

        select.on('change', function() {

            var channel = $(this).val();
            var titleCasedChannel = channel.replace(
                channel.charAt(0),
                channel.charAt(0).toUpperCase());

            // Empty the fallback property so that the Ajax
            // requests will not incorrectly follow the fallback path.
            dataSet.fallback = '';

            dataSet.channel = channel;

            // update the heading text to reflect the new channel
            headingTxt = heading.data('heading').replace('{channel}', titleCasedChannel);
            heading.text(headingTxt);

            aduBySignature(null, dataSet);
        });
    }

    /**
     * Sets up the data for the graph
     * @param {object} panel - The graph panel container.
     * @param {object} [dataSet] - Object containing all data attribute values
     */
    function aduBySignature(panel, dataSet) {

        // if the panel is null, use the provided dataSet
        dataSet = panel ? panel[0].dataset : dataSet;
        var container = $('.adubysig-graph');
        var noDataContainer = $('.no-data', panel);

        // show the loading graph spinner
        var loader = $('#loading-graph');
        loader.removeClass('hide');

        var params = {
            product_name: dataSet.product,
            days: dataSet.days,
            signature: dataSet.signature,
            channel: dataSet.channel
        };
        var url = dataSet.jsonurl + '?' + $.param(params);

        $.getJSON(url, function(data) {

            loader.addClass('hide');
            $('svg', container).empty().attr({
                width: 0,
                height: 0
            });

            noDataContainer.addClass('hide');

            if (data.total) {

                container.removeClass('hide');

                if (dataSet.fallback) {
                    // if there was no version passed to report/list
                    // we fallback to nightly and need to provide the
                    // user with a way to switch between release channels.
                    addChannelSelector(dataSet);
                    drawGraph(data.hits, container);
                } else {
                    drawGraph(data.hits, container);
                }
            } else {
                noDataContainer.removeClass('hide');
            }
        })
        .fail(function(jQXhr, textStatus, errorThrown) {
            var error = 'text status: ' + textStatus;

            if(errorThrown) {
                error += ' error: ' + errorThrown;
            }

            noDataContainer.empty()
                .text('Error while loadng data: ' + error)
                .removeClass('hide');
        });
    }

    return {
       draw: function(panel) {
            aduBySignature(panel);
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
               $('.inner', $panel).html(response);
               $('.loading-placeholder', $panel).hide();

               Plot.draw($panel);

               deferred.resolve();
           });
           req.fail(function(data, textStatus, errorThrown) {
               $('.loading-failed', $panel).show();
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
