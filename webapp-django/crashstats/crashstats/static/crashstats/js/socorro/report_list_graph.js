/* global $, socorro */

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

    var container;

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

        // Even though there was some data returned from the Ajax call
        // the above filter function might filter this out of the result
        // set. Ensure we still have data before proceeding to draw the graph.
        if (finalData.length) {
            var dims = new Dimensions({
                width: 800,
                height: 250,
                marginTop: 25,
                marginLeft: 65,
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

                    // using event.pageX as apposed to pos[0] gives a more accurate
                    // positioning for the x coordinate.
                    var calcX = parseInt(d3.event.pageX, 16) - 55;
                    tooltip.style('display', 'block')
                        .style('top', pos[1] + 'px')
                        .style('left', calcX + 'px')
                        .style('opacity', 1)
                        .html(tooltipContentContainer.html());
                })
                .on('mouseout', function(d) {
                    tooltip.transition().style('opacity', 0);
                });

            entered.transition()
                .duration(600)
                .style('opacity', 1);
        } else {
            container.before($('<p />', {
                class: 'user-feedback info',
                text: 'Insufficient data to draw graph.'
            }));
        }
    }

    /**
     * Removes a user feedback message
     * @param {object} container - The message container to remove.
     */
    function removeMessage(container) {
        container.animate({ opacity: 0 }, 500, function() {
            $(this).remove();
        });
    }

    /**
     * Displays a list of error messages.
     * @param {object} form - The form to prepend the messages to as a jQuery object.
     * @param {array} errors - The array of error messages to prepend.
     */
    function showFormErrors(form, errors) {
        var errorsLength = errors.length;

        var errorsContainer = $('<ul />', { class: 'user-msg error' });

        for (var i = 0; i < errorsLength; i++) {
            errorsContainer.append($('<li />', {
                text: errors[i]
            }));
        }
        form.prepend(errorsContainer);
    }

    /**
     * Validates the form fields
     * @param {object} form - The form as jQuery object
     * @return False or the valid form object
     */
    function isValid(form) {

        var errors = [];

        // Clear any previous messages
        $('.user-msg').remove();

        var endDate = $('#end_date', form).val();
        var startDate = $('#start_date', form).val();

        if (socorro.date.isFutureDate(endDate) || socorro.date.isFutureDate(startDate)) {
            errors.push('Dates cannot be in the future.');
        }

        if (!socorro.date.isValidDuration(startDate, endDate, 'less')) {
            errors.push('The start date should be after the end date.');
        }

        if (errors.length > 0) {
            showFormErrors(form, errors);
            return false;
        }

        return form;
    }

    /**
     * Sets up the data for the graph
     * @param {object} panel - The graph panel container.
     */
    function aduBySignature(panel) {

        container = $('.adubysig-graph');

        var loader = $('.loading-graph', panel);
        var msgContainer = $('.user-feedback', container);

        dataSet = panel[0].dataset;

        container.removeClass('hide');
        loader.removeClass('hide');

        var formParams = $(':input:not([name="csrfmiddlewaretoken"])', panel).serialize();
        var params = {
            product_name: dataSet.product,
            signature: dataSet.signature
        };

        var url = dataSet.jsonurl + '?' + $.param(params) + '&' + formParams;

        $.getJSON(url, function(data) {

            loader.addClass('hide');
            removeMessage(msgContainer);

            if (data.total) {
                $('svg', container).empty();
                drawGraph(data.hits, container);
            } else {
                // collapse the svg container so that it does not take up
                // any space when there is no data returned.
                $('svg', container).empty().attr({
                    width: 0,
                    height: 0
                });

                container.before($('<p />', {
                    class: 'user-feedback info',
                    text: 'No data returned for signature '  + dataSet.signature
                }));
            }
        })
        .fail(function(jQXhr, textStatus, errorThrown) {
            var error = 'text status: ' + textStatus;

            if(errorThrown) {
                error += ' error: ' + errorThrown;
            }

            loader.addClass('hide');
            removeMessage(msgContainer);

            container.before($('<p />', {
                class: 'user-feedback error',
                text: 'Error while loading data ' + error
            }));
        });
    }

    return {
       draw: function(panel) {
            aduBySignature(panel);
       },
       /**
        * Registers the form submit handler and calls aduBySignature
        * if the form is valid.
        * @param {object} panel - The tab container as jQuery object
        */
       registerForm: function(panel) {

           var form = $('form', panel);

           form.on('submit', function(event) {
               event.preventDefault();

               // remove any currently displayed error or
               // no data messages.
               removeMessage($('.user-feedback', panel));

               // if the form is valid, pass values to the
               // ajax call. If invalid, the function will
               // handle the errors.
               if (isValid(form)) {
                   aduBySignature(panel);
               }
           });
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

               // handle submit events from the form.
               Plot.registerForm($panel);
               // draw the graph using initial data
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
