/* global socorro:true, $:true */

$(function () {
    'use strict';

    // parameters
    var searchSection = $('#search-form');
    var form = $('form', searchSection);
    var fieldsURL = form.data('fields-url');
    var SIGNATURE = form.data('signature');
    var panelsNavSection = $('#panels-nav');

    var pageNum = 1;  // the page number as passed in the URL

    var initializedTabs = {};
    var tabsLoadFunctions = {};

    function getParamsWithSignature() {
        var params = form.dynamicForm('getParams');
        params.signature = SIGNATURE;
        return params;
    }

    function loadTab(tabName) {
        if (!initializedTabs[tabName]) {
            initializedTabs[tabName] = true;
            tabsLoadFunctions[tabName]();
        }
    }

    function showTab(tabName) {
        $('.selected', panelsNavSection).removeClass('selected');
        $('.' + tabName, panelsNavSection).addClass('selected');

        Analytics.trackTabSwitch('signature_report', tabName);

        loadTab(tabName);

        // Hide all main panels.
        $('#mainbody > .panel').hide();
        // Then show the one for our tab.
        $('#' + tabName + '-panel').show();
    }

    function loadInitialTab() {
        var currentTab = window.location.hash.substring(1);

        if (!currentTab) {
            currentTab = 'reports'; // the default tab
        }

        showTab(currentTab);
    }

    function startSearchForm(callback) {
        var queryString = window.location.search.substring(1);
        var initialParams = socorro.search.parseQueryString(queryString);
        if (initialParams) {
            if (initialParams.page) {
                pageNum = initialParams.page;
            }
            if (initialParams.signature) {
                delete initialParams.signature;
            }

            initialParams = socorro.search.getFilteredParams(initialParams);
            form.dynamicForm(fieldsURL, initialParams, '#search-params-fieldset', function () {
                // When the form has finished loading, we get sanitized parameters
                // from it and show the results. This will avoid strange behaviors
                // that can be caused by manually set parameters, for example.
                callback();
            });
        }
        else {
            // No initial params, just load the form and let the user play with it.
            form.dynamicForm(fieldsURL, {}, '#search-params-fieldset');
            callback();
        }

        form.hide();
    }

    function addLoaderToElt(elt) {
        elt.append($('<div>', {class: 'loader'}));
    }

    function bindPaginationLinks(panel, callback) {
        $('.pagination a', panel).click(function (e) {
            e.preventDefault();

            var page = $(this).data('page');
            callback(page);
        });
    }

    function handleError(contentElt, jqXHR, textStatus, errorThrown) {
        var errorContent = $('<div>', {class: 'error'});

        try {
            var errorDetails = $(jqXHR.responseText); // This might fail
            var errorTitle = 'Oops, an error occured';
            var errorMsg = 'Please fix the following issues: ';

            errorContent.append($('<h3>', {text: errorTitle}));
            errorContent.append($('<p>', {text: errorMsg}));
            errorContent.append(errorDetails);
        }
        catch (e) {
            // If an exception occurs, that means jQuery wasn't able
            // to understand the status of the HTTP response. It is
            // probably a 500 error. We thus show a different error.
            var errorTitle = 'An unexpected error occured :(';
            var errorMsg = 'We have been automatically informed of that error, and are working on a solution. ';
            var errorDetails = textStatus + ' - ' + errorThrown;

            errorContent.append($('<h3>', {text: errorTitle}));
            errorContent.append($('<p>', {text: errorMsg}));
            errorContent.append($('<p>', {text: errorDetails}));
        }

        contentElt.empty().append(errorContent);
    }

    function bindEvents() {
        searchSection.on('click', '.new-line', function (e) {
            e.preventDefault();
            form.dynamicForm('newLine');
        });

        searchSection.on('click', 'button[type=submit]', function (e) {
            e.preventDefault();
            var params = getParamsWithSignature();
            var queryString = '?' + $.param(params, true);
            window.location.search = queryString;
        });

        // Show or hide filters.
        searchSection.on('click', '.toggle-filters', function (e) {
            e.preventDefault();

            var elt = $(this);
            form.toggle();
            elt.toggleClass('show');
            if (elt.hasClass('show')) {
                elt.html('Show');
            }
            else {
                elt.html('Hide');
            }
        });

        // Change tab using navigation links.
        panelsNavSection.on('click', 'a', function (e) {
            showTab($(this).data('tab-name'));
        });
    }

    tabsLoadFunctions.reports = function () {
        // Initialize the reports tab, bind all events and start loading
        // default data.
        var reportsPanel = $('#reports-panel');
        var contentElt = $('.content', reportsPanel);
        var columnsInput = $('input[name=_columns_fake]', reportsPanel);

        var dataUrl = reportsPanel.data('source-url');

        // Make the columns input sortable.
        columnsInput.select2({
            'data': window.FIELDS,
            'multiple': true,
            'width': 'element'
        });
        columnsInput.on("change", function() {
            $('input[name=_columns]').val(columnsInput.val());
        });
        columnsInput.select2('container').find('ul.select2-choices').sortable({
            containment: 'parent',
            start: function() {
                columnsInput.select2('onSortStart');
            },
            update: function() {
                columnsInput.select2('onSortEnd');
            }
        });

        function prepareResultsQueryString(params, page) {
            var i;
            var len;

            var columns = columnsInput.select2('data');
            if (columns) {
                params._columns = [];
                for (i = 0, len = columns.length; i < len; i++) {
                    params._columns[i] = columns[i].id;
                }
            }

            // Add the page number.
            params.page = page || pageNum;

            var queryString = $.param(params, true);
            return '?' + queryString;
        }

        function showReports(page) {
            // Remove previous results and show loader.
            contentElt.empty();
            addLoaderToElt(contentElt);

            var params = getParamsWithSignature();
            var url = prepareResultsQueryString(params, page);
            window.history.replaceState(params, null, url);

            $.ajax({
                url: dataUrl + url,
                success: function(data) {
                    contentElt.empty().append($(data));
                    $('.tablesorter').tablesorter();
                    bindPaginationLinks(reportsPanel, showReports);
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    handleError(contentElt, jqXHR, textStatus, errorThrown);
                },
                dataType: 'HTML'
            });
        }

        reportsPanel.on('click', '.controls button[type=submit]', function (e) {
            e.preventDefault();
            showReports();
        });

        showReports();
    };

    tabsLoadFunctions.aggregations = function () {
        var aggregationsPanel = $('#aggregations-panel');
        var statusElt = $('.status', aggregationsPanel);
        var contentElt = $('.content', aggregationsPanel);
        var selectElt = $('.fields-list', aggregationsPanel);

        var dataUrl = aggregationsPanel.data('source-url');

        function disableOption(field) {
            $('option[value=' + field + ']', selectElt).prop('disabled', true);
        }

        function enableOption(field) {
            $('option[value=' + field + ']', selectElt).prop('disabled', false);
        }

        function makePanelHeader(field) {
            return field.charAt(0).toUpperCase() +
                field.slice(1).replace(/_/g, ' ');
        }

        function showAggregation(field) {
            // Initialize aggregation panel with heading.
            var panelElt = $('<div>', {class: 'panel'});
            var headerElt = $('<header>', {class: 'title'});
            var bodyElt = $('<div>', {class: 'body'});
            var deleteButton = $('<a>', {href: '#', class: 'options delete', text: 'X'})


            headerElt.append(
                deleteButton,
                $('<h2>', {text: makePanelHeader(field)})
            );
            panelElt.append(headerElt, bodyElt);

            deleteButton.click(function (e) {
                e.preventDefault();
                panelElt.remove();
                enableOption(field);
            });

            // Remove previous results and show loader.
            statusElt.empty();
            disableOption(field);
            contentElt.append(panelElt);
            addLoaderToElt(bodyElt);

            var params = getParamsWithSignature();
            var url = dataUrl + field + '/?' + $.param(params, true);

            $.ajax({
                url: url,
                success: function(data) {
                    statusElt.empty();
                    var dataElt = $(data);
                    bodyElt.empty().append(dataElt);
                    $('.tablesorter').tablesorter();
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    handleError(statusElt, jqXHR, textStatus, errorThrown);
                },
                dataType: 'HTML'
            });
        }

        // Prepare the list of fields.
        selectElt.select2({
            'placeholder': 'Aggregate on...',
            'allowClear': true
        });

        selectElt.on('change', function (e) {
            selectElt.select2('val', '');
            showAggregation(e.val);
        });

        showAggregation('product');
        showAggregation('platform');
        showAggregation('build_id');
    };

    tabsLoadFunctions.comments = function () {
        // Initialize the comments tab, bind all events and start loading
        // default data.
        var commentsPanel = $('#comments-panel');
        var contentElt = $('.content', commentsPanel);

        var dataUrl = commentsPanel.data('source-url');

        function showComments(page) {
            // Remove previous results and show loader.
            contentElt.empty();
            addLoaderToElt(contentElt);

            var params = getParamsWithSignature();
            params.page = page || pageNum;

            var queryString = $.param(params, true);
            var url = dataUrl + '?' + queryString;

            $.ajax({
                url: url,
                success: function(data) {
                    contentElt.empty().append($(data));
                    $('.tablesorter').tablesorter();
                    bindPaginationLinks(commentsPanel, showComments);
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    handleError(contentElt, jqXHR, textStatus, errorThrown);
                },
                dataType: 'HTML'
            });
        }

        showComments();
    };

    tabsLoadFunctions.graph = function() {

        // Initialize the graph tab, bind all events and start loading
        // default data.
        var graphPanel = $('#graph-panel');
        var contentElt = $('.content', graphPanel);
        var loaderElt = $('.loader', graphPanel);
        var selectElt = $('.channels-list', graphPanel);
        var graphElt = $('.adu-graph', graphPanel);

        // Get the url from graphPanel.
        var dataUrl = graphPanel.data('source-url');

        // Set the default channel.
        var defaultChannel = window.DEFAULT_CHANNEL;

        // Puts JSON data into the correct format for the graph.
        function formatData(data) {
            // Nest on build IDs and sum the counts.
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

            // Cut off the bottom 20% of ADU counts.
            var adus = finalData.map(function(d) {
                return d.values.adu_count;
            });
            adus.sort(d3.ascending);
            var cutoff = d3.quantile(adus, 0.2);
            finalData = finalData.filter(function(d) {
                return d.values.adu_count >= cutoff;
            });

            finalData = finalData.map(function(d) {
                return {
                    'build_id': d.key,
                    'date': d.key,
                    'ratio': d.values.ratio,
                    'adu_count': d.values.adu_count,
                    'crash_count': d.values.crash_count
                };
            });
            // Convert build IDs to dates and make the format nicer.
            MG.convert.date(finalData, 'date', '%Y%m%d%H%M%S');
            return finalData;
        }

        // Draws the graph.
        function drawGraph(data) {
            MG.data_graphic({
                data: data,
                chart_type: 'point',
                full_width: true,
                target: '#adu-graph',
                x_accessor: 'date',
                y_accessor: 'ratio',
                xax_start_at_min: true,
                decimals: 10,
                area: false,
                mouseover: function(d, i) {
                    $('.mg-active-datapoint')
                        .html('Build ID: ' + data[i].build_id +
                            ', ADU count: ' + data[i].adu_count +
                            ', Crash count: ' + data[i].crash_count
                        );
                }
            });
        }

        // Success function for the JSON request.
        function onJsonLoad(data) {
            // Remove loader.
            graphElt.empty();
            if (data.total) {
                drawGraph(formatData(data.hits));
            } else {
                $('#adu-graph').text('No results were found.');
            }
        }

        // Error function.
        function error(jqXHR, textStatus, errorThrown) {
            handleError(contentElt, jqXHR, textStatus, errorThrown);
        }

        function showGraph(channel) {
            // Remove previous results and show loader.
            graphElt.empty();
            addLoaderToElt(graphElt);

            // Make graph options from form. Mandatory params for graph:
            // product_name, signature, start_date, end_date, channel
            // Dates will be processed by Django; others processed here.
            var params = getParamsWithSignature();

            // Channel and signature should be defined.
            var graphOptions = {
                channel: channel,
                signature: params.signature
            };

            // Product may be undefined. If so, user must choose one.
            if (params.product) {
                graphOptions.product = params.product[0];
            } else {
                // Show the search form.
                var elt = $('.toggle-filters');
                elt.removeClass('show');
                elt.html('Hide');
                form.show();
                // Add a new fieldset for choosing a product.
                form.dynamicForm('newLine', {
                    field: 'product',
                    operator: 'has terms',
                    value: ''
                });
                // Focus the value input of the new fieldset.
                $('fieldset:last-child .value').select2('open');
                // Prompt the user to choose a product.
                contentElt.empty().text('Please select a product.');
                return;
            }

            var url = dataUrl + channel + '/?' + $.param(params, true);
            // Get graph data and draw graph.
            $.ajax({
                url: url,
                success: onJsonLoad,
                error: error,
                dataType: 'json'
            });

        }

        // Apply select2 to select element.
        selectElt.select2({
            'placeholder': 'Channel...',
            'allowClear': true
        });

        // Draw a new graph whenever a new channel is chosen.
        selectElt.on('change', function (e) {
            selectElt.select2('val', '');
            showGraph(e.val);
        });

        // Show graph on load with default options.
        showGraph(defaultChannel);
    };

    // Finally start the damn thing.
    bindEvents();
    startSearchForm(loadInitialTab);
});
