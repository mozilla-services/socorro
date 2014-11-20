$(function () {
    'use strict';

    // parameters
    var form = $('#search-form form');
    var fieldsURL = form.data('fields-url');
    var resultsURL = form.data('results-url');
    var customURL = form.data('custom-url');
    var publicApiUrl = form.data('public-api-url');

    var submitButton = $('button[type=submit]', form);
    var newLineBtn = $('.new-line');
    var customizeBtn = $('.customize');

    var contentElt = $('#search_results');
    var optionsElt = $('fieldset.options', form);
    var facetsInput = $('input[name=_facets]', form);
    var columnsInput = $('input[name=_columns_fake]', form);
    var publicApiUrlInput = $('input[name=_public_api_url]', form);

    function showResults(url) {
        // Show loader.
        try {
            contentElt.tabs('destroy');
        }
        catch (e) {}
        contentElt.empty().append($('<div>', {'class': 'loader'}));

        // If a tracker is available, track that AJAX call.
        window.socorroTrackUse(url);

        $.ajax({
            url: url,
            success: function(data) {
                contentElt.empty().append(data).tabs();
                $('.tablesorter').tablesorter();

                // Enhance bug links.
                BugLinks.enhance();
            },
            error: function(jqXHR, textStatus, errorThrown) {
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
            },
            dataType: 'HTML'
        });
    }

    function prepareResultsQueryString(params) {
        var i;
        var len;

        var facets = facetsInput.select2('data');
        if (facets) {
            params._facets = [];
            for (i = 0, len = facets.length; i < len; i++) {
                params._facets[i] = facets[i].id;
            }
        }

        var columns = columnsInput.select2('data');
        if (columns) {
            params._columns = [];
            for (i = 0, len = columns.length; i < len; i++) {
                params._columns[i] = columns[i].id;
            }
        }

        var queryString = $.param(params, true);
        return '?' + queryString;
    }

    function updatePublicApiUrl(params) {
        // Update the public API URL.
        var queryString = $.param(params, true);
        publicApiUrlInput.val(BASE_URL + publicApiUrl + '?' + queryString);
    }

    function sortResults(results, container, query) {
        if (query.term) {
            return results.sort(function (a, b) {
                if (a.text.length > b.text.length) {
                    return 1;
                }
                else if (a.text.length < b.text.length) {
                    return -1;
                }
                else {
                    return 0;
                }
            });
        }
        return results;
    }

    /**
     * Simple Search UI with a limited number of fields.
     */
    var SimpleSearch = {
        container: $('#simple-search'),
        initialized: false
    };

    SimpleSearch.initialize = function () {
        if (this.initialized) {
            return;
        }

        $('input[type=text]', this.container).select2({
            'width': 'element',
            'tags': []
        });
        $('select', this.container).select2({
            'width': 'element',
            'closeOnSelect': false
        });

        this.initialized = true;
    };

    SimpleSearch.getParams = function () {
        var params = {};
        $('select', this.container).each(function (i, item) {
            var name = item.name;
            var value = $(item).select2('val');
            if (value.length) {
                params[name] = value;
            }
        });
        return params;
    };

    SimpleSearch.setParams = function (params) {
        $('select', this.container).each(function (i, item) {
            if (item.name in params) {
                $(item).select2('val', params[item.name]);
            }
        });
    };

    SimpleSearch.addTerm = function (name, value) {
        var field = $('select[name=' + name + ']', this.container);
        if (field) {
            var values = field.select2('val');
            values.push(value);
            field.select2('val', values);
        }
    };

    SimpleSearch.onpopstate = function (e) {
        var queryString;
        var params = e.state;

        if (params === null) {
            // No state was added, check if the URL contains parameters
            queryString = window.location.search.substring(1);
            params = socorro.search.parseQueryString(queryString);
        }

        if (params) {
            // If there are some parameters, fill the form with those params
            // and run the search and show results.
            queryString = $.param(params, true);
            showResults(resultsURL + '?' + queryString);
            this.setParams(params);
            updatePublicApiUrl(params);
        }
        else {
            // If there are no parameters, empty the form and show the
            // default content.
            $('select', this.container).select2('val', null);
            contentElt.empty().append($('<p>', {'text': 'Run a search to get some results. '}));
        }
    };

    SimpleSearch.activate = function (params) {
        // It's better to show this before initializing it, because otherwise
        // select2 has troubles computing the size of the select elements.
        this.container.show();

        if (!this.initialized) {
            this.initialize();
        }

        if (params) {
            this.setParams(params);
        }

        window.onpopstate = this.onpopstate;
    };

    SimpleSearch.deactivate = function () {
        this.container.hide();
    };

    /**
     * Advanced Super Search UI with all options.
     */
    var AdvancedSearch = {
        container: $('#advanced-search'),
        initialized: false
    };

    AdvancedSearch.initialize = function (initialParams) {
        if (this.initialized) {
            return;
        }

        newLineBtn.click(function (e) {
            e.preventDefault();
            form.dynamicForm('newLine');
        });

        customizeBtn.click(function (e) {
            e.preventDefault();
            var params = this.getParams();
            var url = prepareResultsQueryString(params);

            window.location = customURL + url;
        }.bind(this));

        var queryString = window.location.search.substring(1);

        if (!initialParams) {
            initialParams = socorro.search.parseQueryString(queryString);
        }

        if (initialParams) {
            // If there are initial params, that means we should run the
            // corresponding search right after the form has finished loading.

            var page = 1;
            if (initialParams.page) {
                page = initialParams.page;
            }

            initialParams = socorro.search.getFilteredParams(initialParams);
            var self = this;
            form.dynamicForm(fieldsURL, initialParams, '#search-params-fieldset', function () {
                // When the form has finished loading, we get sanitized parameters
                // from it and show the results. This will avoid strange behaviors
                // that can be caused by manually set parameters, for example.
                var params = self.getParams();
                updatePublicApiUrl(params);

                params.page = page;
                var url = prepareResultsQueryString(params);
                showResults(resultsURL + url);
            }, sortResults);
        }
        else {
            // No initial params, just load the form and let the user play with it.
            form.dynamicForm(fieldsURL, null, '#search-params-fieldset', null, sortResults);
        }

        this.initialized = true;
    };

    AdvancedSearch.getParams = function () {
        return form.dynamicForm('getParams');
    };

    AdvancedSearch.setParams = function (params) {
        form.dynamicForm('setParams', params);
    };

    AdvancedSearch.addTerm = function (name, value) {
        form.dynamicForm('newLine', {
            field: name,
            operator: '=', // will fall back to the default operator if 'is exactly' is not implemented for that field
            value: value
        });
    };

    AdvancedSearch.activate = function (params) {
        if (!this.initialized) {
            this.initialize(params);
        }
        else {
            this.setParams(params);
        }

        this.container.show();
        window.onpopstate = this.onpopstate;
    };

    AdvancedSearch.deactivate = function () {
        this.container.hide();
    };

    AdvancedSearch.onpopstate = function (e) {
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
            queryString = $.param(params, true);
            showResults(resultsURL + '?' + queryString);
            params = socorro.search.getFilteredParams(params);
            updatePublicApiUrl(params);
            this.setParams(params);
        }
        else {
            // If there are no parameters, empty the form and show the default content
            form.dynamicForm('setParams', {});
            form.dynamicForm('newLine');
            contentElt.empty().append($('<p>', {'text': 'Run a search to get some results. '}));
        }
    };

    /*--- Logic to switch mode (Simple and Advanced) <--- */
    var currentMode = null;

    function activateSimpleMode(params) {
        AdvancedSearch.deactivate();
        SimpleSearch.activate(params);

        currentMode = SimpleSearch;
    }
    function activateAdvancedMode(params) {
        SimpleSearch.deactivate();
        AdvancedSearch.activate(params);

        currentMode = AdvancedSearch;
    }

    if ($('#ui-mode-switch input[type=checkbox]')[0].checked) {
        activateSimpleMode();
    }
    else {
        activateAdvancedMode();
    }

    form.on('change', '#ui-mode-switch input[type=checkbox]', function () {
        if (this.checked) {
            activateSimpleMode(AdvancedSearch.getParams());
        }
        else {
            activateAdvancedMode(SimpleSearch.getParams());
        }
    });

    submitButton.click(function (e) {
        e.preventDefault();
        var params = currentMode.getParams();
        updatePublicApiUrl(params);

        var url = prepareResultsQueryString(params);
        window.history.pushState(params, 'Search results', url);

        showResults(resultsURL + url);
    });

    // Make every value a link that adds a new line to the form.
    contentElt.on('click', '.term', function (e) {
        e.preventDefault();

        currentMode.addTerm(
            $(this).data('field'),
            $(this).text().trim()
        );

        // And then run the new, corresponding search.
        submitButton.click();
    });

    facetsInput.select2({
        'data': window.FACETS,
        'multiple': true,
        'width': 'element',
        'sortResults': sortResults
    });
    columnsInput.select2({
        'data': window.COLUMNS,
        'multiple': true,
        'width': 'element',
        'sortResults': sortResults
    });

    // Make the columns input sortable
    columnsInput.on("change", function() {
        $("input[name=_columns]").val(columnsInput.val());
    });

    columnsInput.select2("container").find("ul.select2-choices").sortable({
        containment: 'parent',
        start: function() {
            columnsInput.select2("onSortStart");
        },
        update: function() {
            columnsInput.select2("onSortEnd");
        }
    });

    // Show or hide advanced options
    $('h4', optionsElt).click(function (e) {
        $('h4 + div', optionsElt).toggle();
        $('span', this).toggle();
    });
    $('h4 + div', optionsElt).hide();
});
