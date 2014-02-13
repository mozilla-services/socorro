/*global socorro:false, $:false, nv:false, d3:false */

$(function() {
    'use strict';
    var supportedProducts = ['Firefox'];

    /**
     * Takes a specified array of form fields and returns an
     * encoded array ready for use in Ajax calls.
     * @param {array} fields - Array of field objects
     */
    function getParams(fields) {
        var params = [];

        $.each(fields, function(index, field) {
            var name = field.attr('name');
            var value = field.val();

            // Dates displayed in the UI is not in a format accepted by the middleware so,
            // if a field is of type=date, convert it to ISO_STANDARD before adding to
            // parameter object.
            if (field.attr('type') === 'date') {
                value = socorro.date.formatDate(new Date(field.val()), "ISO_STANDARD");
            }

            params.push({
                name: name,
                value: value
            });
        });

        return $.param(params);
    }

    var baseUrl = '/gccrashes/json_data/';
    var productSelector = $('#product');
    var versionSelector = $('#version');

    /**
     * Builds the URL for getJSON call
     * @returns returns the ajaxUrl
     */
    function buildUrl() {
        var product = 'products/' + productSelector.val();
        var version = '/versions/' + versionSelector.val();

        var params = getParams([$("#start_date"), $("#end_date")]);

        return baseUrl + product + version + '?' + params;
    }

    var graphContainer = $('#gccrashes_graph');

    /**
     * Draws the graph.
     * @param {string} ajaxUrl - The url end point from which to retrieve data.
     */
    function plotGraph(ajaxUrl) {
        $.getJSON(ajaxUrl, function(data) {

            // Only set the dimensions of the container if there is actual data.
            if (data.total > 0) {
                graphContainer.addClass('gccrashes_graph');
            }
            socorro.ui.removeLoader();

            var items = data.hits;
            var graphData = {};
            graphData.key = data.total;
            graphData.values = [];

            for (var item in items) {
                var currentItem = {
                    "label": items[item][0],
                    "value": items[item][1]
                };
                graphData.values.push(currentItem);
            }

            nv.addGraph(function() {
                var graph = nv.models.discreteBarChart()
                    .x(function(d) {
                        return d.label;
                    })
                    .y(function(d) {
                        return d.value;
                    })
                    .margin({ bottom: 120 })
                    .color(["#058DC7", "#ED561B", "#50B432", "#990099"])
                    .staggerLabels(false)
                    .tooltips(true)
                    .showValues(false)
                    .tooltipContent(function(key, y, e, graph) {
                        return '<h4 class="graph-tooltip-header">' + y + '</h4><p class="graph-tooltip-body">' + graph.value + '</p>';
                    })
                    .transitionDuration(500);

                graph.yAxis
                     .axisLabel('GC Crashes per 1M ADI by Build ID')
                     .axisLabelDistance(30)
                     .tickFormat(d3.format(',d'));

                d3.select('#gccrashes_graph svg')
                  .datum([graphData])
                  .call(graph);

                var xTicks = d3.select('.nv-x').selectAll('g.tick text');
                xTicks.attr('transform', 'translate (-10, 60) rotate(-90 0, 0)');

                nv.utils.windowResize(graph.update);

                return graph;
            });
        });
    }

    /* When the document is ready, plot the graph */
    socorro.ui.setLoader(graphContainer);
    plotGraph(buildUrl());

    var gccrashesForm = $('#gccrashes');

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
     * Validates the current form and return true or
     * an errors array.
     * @param {object} form - The form as a jQuery object.
     */
    function isValid(form) {
        var errors = [];

        // Clear any previous messages
        $('.user-msg').remove();

        var selectedProduct = $('#product').val();
        var selectedVersion = $('#version').val();
        var endDate = $('#end_date', form).val();
        var startDate = $('#start_date', form).val();

        if (socorro.date.isFutureDate(endDate) || socorro.date.isFutureDate(startDate)) {
            errors.push('Dates cannot be in the future.');
        }

        if (!socorro.date.isValidDuration(startDate, endDate, 'less')) {
            errors.push('The from date should be less than the to date.');
        }

        if(selectedProduct === 'none') {
            errors.push('Please select a product.');
        }

        if(selectedVersion === 'none') {
            errors.push('Please select a version.');
        }

        if (errors.length > 0) {
            showFormErrors(form, errors);
            return false;
        }

        return true;
    }

    gccrashesForm.on('submit', function(event) {

        event.preventDefault();

        if (isValid(gccrashesForm)) {
            // Clear out the SVG container
            $('svg', graphContainer).empty();
            // Remove class from container so it will collapse.
            graphContainer.removeClass('gccrashes_graph');

            socorro.ui.setLoader(graphContainer);
            plotGraph(buildUrl());
        }
    });

    productSelector.on('change', function() {
        var product = $(this).val();

        if ($.inArray(product, supportedProducts) === -1) {
            var response = {
                status: 'error',
                message: 'Report currently only supports ' + supportedProducts.toString()
            };
            socorro.ui.setUserMsg('#gccrashes', response);
        } else {
            // Ensure there are no user message that linger when
            // a supported product is selected.
            socorro.ui.removeUserMsg('#gccrashes');
        }
    });

    var dateFields = $("#gccrashes input[type='date']");

    //check if the HTML5 date type is supported else, fallback to jQuery UI
    if(!socorro.dateSupported()) {
        dateFields.datepicker({
            dateFormat: "yy/mm/dd"
        });
    }
});
