/*global socorro:false, $:false, nv:false, d3:false */

$(function() {
    'use strict';
    var supportedProducts = ['Firefox'];

    var gccrashesForm = $('#gccrashes');
    var baseUrl = gccrashesForm.data('base-url');

    var productSelector = $('#product');
    var versionSelector = $('#version');
    var startDateElem = $("#start_date");
    var endDateElem = $("#end_date");

    /**
     * Builds the URL for plotGraph
     * @param {object} form - A jQuery form object to serialize
     * @returns returns the ajaxUrl
     */
    function buildUrl(form) {
        var params = form.find(':input:not(:hidden)').serialize();
        return baseUrl + '?' + params;
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

                // Only do the transform on the ticks if we actually have data.
                if (graphData.key > 0) {
                    var xTicks = d3.select('.nv-x').selectAll('g.tick text');
                    xTicks.attr('transform', 'translate (-10, 60) rotate(-90 0, 0)');
                } else {
                    // Do not clip the No Data text
                    d3.select('.nv-noData')
                      .attr('dy', '0');

                }

                nv.utils.windowResize(graph.update);

                return graph;
            });
        });
    }

    // Do not try to load graph data if there were django form
    // validation errors.
    if (!$('.django-form-error').length) {
        socorro.ui.setLoader(graphContainer);
        plotGraph(buildUrl(gccrashesForm));
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
     * Validates the current form and return true or
     * an errors array.
     * @param {object} form - The form as a jQuery object.
     */
    function isValid(form) {
        var errors = [];

        // Clear any previous messages
        $('.user-msg').remove();

        var selectedProduct = productSelector.val();
        var selectedVersion = versionSelector.val();
        var endDate = endDateElem.val();
        var startDate = startDateElem.val();

        if (socorro.date.isFutureDate(endDate) || socorro.date.isFutureDate(startDate)) {
            errors.push('Dates cannot be in the future.');
        }

        if (!socorro.date.isValidDuration(startDate, endDate, 'less')) {
            errors.push('The from date should be less than the to date.');
        }

        if (errors.length > 0) {
            showFormErrors(form, errors);
            return false;
        }

        return true;
    }

    /**
     * Sets the document title and the page heading to the newly
     * selected version.
     * @param {string} selectedVersion - The version to update to.
     */
    function setTitle(selectedVersion) {
        var params = window.location.search;
        var pageHeading = $('#gcc-main-title');
        var tmpl = pageHeading.data('template');
        var newTitle = tmpl.replace('$VERSION', selectedVersion);

        pageHeading.text(newTitle);
        document.title = newTitle;
    }

    var state = {};
    /**
     * Updates the URL and changes the browser history using replace state
     * to ensure URLs are always bookmarkable.
     * @param {string} selectedVersion - The version to update to.
     */
    function setHistory(selectedVersion) {
        var historyEntry = '';
        var params = window.location.search || '?' + $('input[type="date"]').serialize();

        if (window.location.pathname.indexOf('versions') === -1) {
            historyEntry = window.location.pathname + '/versions/' + selectedVersion;
            history.replaceState(state, document.title, historyEntry + params);
        } else {
            var paths = window.location.pathname.split('/');
            paths[paths.length - 1] = selectedVersion;

            historyEntry = paths.join('/');
            history.replaceState(state, document.title, historyEntry + params);
        }
    }

    gccrashesForm.on('submit', function(event) {

        event.preventDefault();

        if (isValid(gccrashesForm)) {
            var selectedVersion = $('#version', gccrashesForm).val();

            // Clear out the SVG container
            $('svg', graphContainer).empty();
            // Remove class from container so it will collapse.
            graphContainer.removeClass('gccrashes_graph');

            // Set title, page heading and update URL/browser history
            setTitle(selectedVersion);
            setHistory(selectedVersion);

            socorro.ui.setLoader(graphContainer);
            plotGraph(buildUrl(gccrashesForm));
        }
    });

    $(startDateElem).add(endDateElem).on('change', function() {
        var pathName = window.location.pathname;
        var params = $('input[type="date"]').serialize();
        history.replaceState(state, document.title, pathName + '?' + params);
    });

    versionSelector.on('change', function() {
        var selectedVersion = versionSelector.val();

        setTitle(selectedVersion);
        setHistory(selectedVersion);
    });

    productSelector.on('change', function() {
        var product = productSelector.val();

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

    var dateFields = $("input[type='date']", gccrashesForm);

    //check if the HTML5 date type is supported else, fallback to jQuery UI
    if(!socorro.dateSupported()) {
        dateFields.datepicker({
            dateFormat: "yy-mm-dd"
        });
    }
});
