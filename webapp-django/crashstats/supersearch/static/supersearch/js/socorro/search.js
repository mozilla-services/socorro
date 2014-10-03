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
        // show loader
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

                // Make every value a link that adds a new line to the form
                $('.term').click(function (e) {
                    e.preventDefault();
                    form.dynamicForm('newLine', {
                        field: $(this).data('field'),
                        operator: '=', // will fall back to the default operator if 'is exactly' is not implemented for that field
                        value: $(this).text().trim()
                    });
                    // And then run the new, corresponding search
                    submitButton.click();
                });
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

    submitButton.click(function (e) {
        e.preventDefault();
        var params = form.dynamicForm('getParams');
        updatePublicApiUrl(params);

        var url = prepareResultsQueryString(params);
        window.history.pushState(params, 'Search results', url);

        showResults(resultsURL + url);
    });

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
            queryString = $.param(params, true);
            showResults(resultsURL + '?' + queryString);
            params = socorro.search.getFilteredParams(params);
            updatePublicApiUrl(params);
            form.dynamicForm('setParams', params);
        }
        else {
            // If there are no parameters, empty the form and show the default content
            form.dynamicForm('setParams', {});
            form.dynamicForm('newLine');
            contentElt.empty().append($('<p>', {'text': 'Run a search to get some results. '}));
        }
    };

    newLineBtn.click(function (e) {
        e.preventDefault();
        form.dynamicForm('newLine');
    });

    customizeBtn.click(function (e) {
        e.preventDefault();
        var params = form.dynamicForm('getParams');
        var url = prepareResultsQueryString(params);

        window.location = customURL + url;
    });

    facetsInput.select2({
        'data': window.FACETS,
        'multiple': true,
        'width': 'element'
    });
    columnsInput.select2({
        'data': window.COLUMNS,
        'multiple': true,
        'width': 'element'
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

    var queryString = window.location.search.substring(1);
    var initialParams = socorro.search.parseQueryString(queryString);
    if (initialParams) {
        // If there are initial params, that means we should run the
        // corresponding search right after the form has finished loading.

        var page = 1;
        if (initialParams.page) {
            page = initialParams.page;
        }

        initialParams = socorro.search.getFilteredParams(initialParams);
        form.dynamicForm(fieldsURL, initialParams, '#search-params-fieldset', function () {
            // When the form has finished loading, we get sanitized parameters
            // from it and show the results. This will avoid strange behaviors
            // that can be caused by manually set parameters, for example.
            var params = form.dynamicForm('getParams');
            updatePublicApiUrl(params);

            params.page = page;
            var url = prepareResultsQueryString(params);
            showResults(resultsURL + url);
        });
    }
    else {
        // No initial params, just load the form and let the user play with it.
        form.dynamicForm(fieldsURL, null, '#search-params-fieldset');
    }
});
