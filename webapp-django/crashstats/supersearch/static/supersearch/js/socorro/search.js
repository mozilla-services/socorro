/*global $ window Analytics */

$(function () {
    'use strict';

    var form = $('#search-form form');
    var resultsURL = form.data('results-url');
    var simpleSearchContainer = $('#simple-search');

    var contentElt = $('#search_results');
    var sortInput = $('input[name=_sort]', form);
    var facetsInput = $('input[name=_facets]', form);
    var columnsInput = $('input[name=_columns_fake]', form);

    /**
     * Run a search.
     *
     * Update the public API URL, push a new history state, query the search
     * results and show them.
     */
    function search(noHistory, page) {
        if (!page) {
            page = 1;
        }

        var params = getParams();
        updatePublicApiUrl(params);

        // Set the page after updating the public API URL, because we don't want
        // that page parameter in the URL. It is only useful in the UI.
        params.page = page;

        var url = prepareResultsQueryString(params);
        queryResults(resultsURL + url);

        if (!noHistory) {
            pushHistoryState(params, url);
        }
    }

    /**
     * Display results from a search query.
     */
    function showResults(data) {
        contentElt.empty().append(data);

        if ($('.no-data', contentElt).length) {
            // There are no results, no need to do more.
            return;
        }

        // Determine which tab should be open. If there is a hash,
        // we let jQuery UI's tabs open the correct one. Otherwise,
        // we want to open the last one of the list.
        var activeTab = null;
        if (!location.hash) {
            activeTab = -1;
        }

        var params = getParams();
        var url = prepareResultsQueryString(params);

        contentElt.tabs({
            active: activeTab,
            activate: function (event, ui) {
                // Make sure the hash is changed when switching tabs.
                var hash = '#' + ui.newPanel.attr('id');
                pushHistoryState(params, url, hash);
            },
            create: function (event, ui) {
                // Put the first tab's id in the hash of the URL.
                var hash = '#' + ui.panel.attr('id');
                pushHistoryState(params, url, hash, true);
            }
        });

        // Handle server-side sorting.
        $('.tablesorter.facet').tablesorter();
        $('#reports-list').tablesorter({
            headers: {
                0: {  // disable the first column, `Crash ID`
                    sorter: false
                }
            }
        });

        // Make sure there are more than 1 page of results. If not,
        // do not activate server-side sorting, rely on the
        // default client-side sorting.
        if ($('.pagination a', contentElt).length) {
            $('.sort-header', contentElt).click(function (e) {
                e.preventDefault();

                var thisElt = $(this);

                // Update the sort field.
                var fieldName = thisElt.data('field-name');
                var sortArr = sortInput.select2('val');

                // First remove all previous mentions of that field.
                sortArr = sortArr.filter(function (item) {
                    return item !== fieldName && item !== '-' + fieldName;
                });

                // Now add it in the order that follows this sequence:
                // ascending -> descending -> none
                if (thisElt.hasClass('headerSortDown')) {
                    sortArr.unshift('-' + fieldName);
                }
                else if (!thisElt.hasClass('headerSortDown') && !thisElt.hasClass('headerSortUp')) {
                    sortArr.unshift(fieldName);
                }

                sortInput.select2('val', sortArr);
                search();
            });
        }

        // Enhance bug links.
        BugLinks.enhance();
    }

    /**
     * Query the search results and show them.
     */
    function queryResults(url) {
        // Show loader.
        try {
            contentElt.tabs('destroy');
        }
        catch (e) {}
        contentElt.empty().append($('<div>', {'class': 'loader'}));

        // If a tracker is available, track that AJAX call.
        Analytics.trackPageview(url);

        $.ajax({
            url: url,
            success: showResults,
            error: function (jqXHR, textStatus, errorThrown) {
                var errorContent = $('<div>', {class: 'error'});

                if (jqXHR.status >= 400 && jqXHR.status < 500) {
                    errorContent.append(
                        $('<h3>', {text: 'Oops, an error occured'})
                    ).append(
                        $('<p>', {text: 'Please fix the following issues:'})
                    ).append($(jqXHR.responseText));
                }
                else {
                    // We have no interest data to display as a constructive
                    // error message to the user. So we'll have to show a
                    // generic error message.
                    errorContent.append(
                        $('<h3>', {text: 'An unexpected error occured :('})
                    ).append(
                        $('<p>', {
                            text: 'We have been automatically informed ' +
                                  'of that error, and are working on a ' +
                                  'solution. '
                        })
                    );
                }

                contentElt.empty().append(errorContent);
            },
            dataType: 'HTML'
        });
    }

    /**
     * Return a query string made from parameters, with the addition of search
     * options (aggregations, columns, sort).
     */
    function prepareResultsQueryString(params) {
        var sortArr = sortInput.select2('data');
        params._sort = sortArr.map(function (x) { return x.id; });

        var facets = facetsInput.select2('data');
        if (facets) {
            params._facets = facets.map(function (x) { return x.id; });
        }

        var columns = columnsInput.select2('data');
        if (columns) {
            params._columns = columns.map(function (x) { return x.id; });
        }

        var queryString = Qs.stringify(params, { indices: false });
        return '?' + queryString;
    }

    /**
     * Update the public API URL field in the form options.
     */
    function updatePublicApiUrl(params) {
        // Update the public API URL.
        var queryString = Qs.stringify(params, { indices: false });
        queryString = queryString.replace(/!/g, '%21');
        $('input[name=_public_api_url]', form).val(
            BASE_URL + form.data('public-api-url') + '?' + queryString
        );
    }

    /**
     * Push a new browser history state.
     */
    function pushHistoryState(params, url, hash, replace) {
        var func = replace && window.history.replaceState || window.history.pushState;
        if (!hash) {
            hash = location.hash;
        }
        func.call(window.history, params, 'Search results', url + hash);
    }

    /**
     * Return the current parameters defined by the search form.
     */
    function getParams() {
        var params = form.dynamicForm('getParams');

        $('select', simpleSearchContainer).each(function (i, item) {
            var name = item.name;
            var value = $(item).select2('val');
            if (value.length) {
                if (params[name]) {
                    params[name] = params[name].concat(value);
                }
                else {
                    params[name] = value;
                }
            }
        });

        return params;
    }

    /**
     * Update the search form with new parameters.
     */
    function setParams(params) {
        function hasOperator(value) {
            var operators = form.dynamicForm('getOperatorsList');
            return operators.some(function (operator) {
                if (operator === 'has') {
                    return false; // we don't care about that one
                }
                return value.indexOf(operator) === 0;
            });
        }

        $('select', simpleSearchContainer).each(function (i, item) {
            if (item.name in params) {
                var values = params[item.name];
                if (!Array.isArray(values)) {
                    values = [values];
                }
                // Sort values, simple ones (with no operator at the start)
                // will go into the simple search select tags, while others
                // will stay in `params` and end up in the advanced form.
                var simpleValues = [];
                params[item.name] = values.map(function (value) {
                    if (!hasOperator(value)) {
                        simpleValues.push(value);
                    }
                    else {
                        return value;
                    }
                });
                $(item).select2('val', simpleValues);
            }
        });
        form.dynamicForm('setParams', params);
    }

    /**
     * Add a new line to the search form with specified field and value.
     * The operator will be 'is exactly' or the default operator for the field.
     */
    function addTerm(name, value) {
        form.dynamicForm('newLine', {
            field: name,
            operator: '=', // will fall back to the default operator if 'is exactly' is not implemented for that field
            value: value
        });
    }

    /**
     * Handler for browser history state changes.
     */
    window.onpopstate = function (e) {
        var queryString;
        var params = e.state;

        if (params === null) {
            // No state was added, check if the URL contains parameters
            queryString = window.location.search.substring(1);
            params = socorro.search.parseQueryString(queryString);
        }

        if (params) {
            // If there are some parameters, fill the form with those params
            // and run the search and show results
            setParams(params);
            search(true);
        }
        else {
            // If there are no parameters, empty the form and show the default content
            form.dynamicForm('setParams', {});
            form.dynamicForm('newLine');
            $('select', simpleSearchContainer).select2('val', null);
            contentElt.empty().append($('<p>', {'text': 'Run a search to get some results. '}));
        }
    };

    /**
     * Initialize the search form, populating it with whatever parameters
     * are passed in the query string.
     */
    function initForm() {
        // Create the simple search form.
        $('input[type=text]', simpleSearchContainer).select2({
            'width': 'element',
            'tags': []
        });
        $('select', simpleSearchContainer).select2({
            'width': 'element',
            'closeOnSelect': false
        });

        // Create the advanced search form.
        var queryString = window.location.search.substring(1);
        var initialParams = socorro.search.parseQueryString(queryString);

        var formCallback = function () {
            // By default, we simply create a new line in the form.
            form.dynamicForm('newLine');
        };

        // If there are initial params, that means we should run the
        // corresponding search right after the form has finished loading.
        if (initialParams) {
            var page = 1;
            if (initialParams.page) {
                page = initialParams.page;
            }
            var dontRun = initialParams._dont_run === '1';

            // Sanitize parameters.
            initialParams = socorro.search.getFilteredParams(initialParams);

            // When the form has finished loading, we get pass it our
            // initial parameters for it to sanitize them. Then we run
            // a regular search, which will use the sane parameters from
            // the dynamicForm library. This will avoid strange behaviors
            // that can be caused by manually set parameters, for example.
            formCallback = function () {
                setParams(initialParams);
                if (!dontRun) {
                    search(false, page);
                }
            };
        }

        form.dynamicForm(
            form.data('fields-url'),
            null,
            '#search-params-fieldset',
            formCallback,
            socorro.search.sortResults
        );
    }

    /**
     * Bind the search buttons' events.
     */
    function initFormButtons() {
        $('button[type=submit]', form).click(function (e) {
            e.preventDefault();
            search();
        });

        $('.new-line', form).click(function (e) {
            e.preventDefault();
            form.dynamicForm('newLine');
        });

        $('.customize', form).click(function (e) {
            e.preventDefault();
            var params = getParams();
            var url = prepareResultsQueryString(params);

            window.location = form.data('custom-url') + url;
        });
    }

    /**
     * Initialize the form options fields, handling aggregations, sorting and more.
     */
    function initFormOptions() {
        var sortFields = [];
        window.COLUMNS.forEach(function (item) {
            sortFields.push(item);
            sortFields.push({
                id: '-' + item.id,
                text: item.text + ' (DESC)',
            });
        });

        sortInput.select2({
            'data': sortFields,
            'multiple': true,
            'width': 'element',
            'sortResults': socorro.search.sortResults,
        });
        facetsInput.select2({
            'data': window.FACETS,
            'multiple': true,
            'width': 'element',
            'sortResults': socorro.search.sortResults,
        });
        columnsInput.select2({
            'data': window.COLUMNS,
            'multiple': true,
            'width': 'element',
            'sortResults': socorro.search.sortResults,
        });

        // Make the columns input sortable
        columnsInput.on("change", function () {
            $("input[name=_columns]").val(columnsInput.val());
        });

        columnsInput.select2("container").find("ul.select2-choices").sortable({
            containment: 'parent',
            start: function () {
                columnsInput.select2("onSortStart");
            },
            update: function () {
                columnsInput.select2("onSortEnd");
            }
        });

        // Show or hide advanced options.
        var optionsElt = $('fieldset.options', form);
        $('h4', optionsElt).click(function (e) {
            $('h4 + div', optionsElt).toggle();
            $('span', this).toggle();
        });
        $('h4 + div', optionsElt).hide();
    }

    /**
     * Bind terms of the results to add new form lines.
     */
    function initContentBinding() {
        // Make every value a link that adds a new line to the form.
        contentElt.on('click', '.term', function (e) {
            e.preventDefault();

            addTerm(
                $(this).data('field'),
                $(this).data('content')
            );

            // And then run the new, corresponding search.
            search();
        });
    }

    /**
     * Start it all!
     */
    function initialize() {
        initForm();
        initFormButtons();
        initFormOptions();
        initContentBinding();
    }
    initialize();
});
