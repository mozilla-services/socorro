$(function () {
    'use strict';

    // parameters
    var fieldsURL = '/search/fields/';
    var resultsURL = '/search/results/';
    var form = $('#search-form form');
    var submitButton = $('button[type=submit]', form);
    var newLineBtn = $('.new-line');
    var contentElt = $('#search_results');
    var facetsInput = $('select[name=_facets]', form);

    function parseQueryString(queryString) {
        var params = {}, queries, temp, i, l;

        // Split into key/value pairs
        queries = queryString.split("&");
        l = queries.length;

        if (l === 1 && queries[0] === '') {
            return false;
        }

        // Convert the array of strings into an object
        for (i = 0; i < l; i++) {
            temp = queries[i].split('=');
            var key = temp[0];
            var value = decodeURIComponent(temp[1]);

            if (params[key] && Array.isArray(params[key])) {
                params[key].push(value);
            }
            else if (params[key]) {
                params[key] = [params[key], value];
            }
            else {
                params[key] = value;
            }
        }

        return params;
    }

    function showResults(url) {
        // show loader
        contentElt.empty().append($('<div>', {'class': 'loader'}));

        $.ajax({
            url: url,
            success: function(data) {
                contentElt.empty().append(data);
            },
            error: function(jqXHR) {
                var errorTitle = 'Oops, an error occured';
                var errorMsg = 'Please fix the following issues: ';

                var errorContent = $('<div>', {class: 'error'});
                errorContent.append($('<h3>', {text: errorTitle}));
                errorContent.append($('<p>', {text: errorMsg}));
                errorContent.append($(jqXHR.responseText));

                contentElt.empty().append(errorContent);
            },
            dataType: 'HTML'
        });
    }

    function getFilteredParams(params) {
        if ('page' in params) {
            delete params.page;
        }
        return params;
    }

    function getFacetsInput() {
        return $('select[name=_facets]', form).val();
    }

    submitButton.click(function (e) {
        e.preventDefault();

        var params = form.dynamicForm('getParams');

        var facets = getFacetsInput();

        if (facets) {
            params._facets = facets;
        }

        var queryString = $.param(params, true);
        var url = '?' + queryString;

        window.history.pushState(params, 'Search results', url);

        showResults(resultsURL + url);
    });

    window.onpopstate = function (e) {
        var queryString;
        var params = e.state;

        if (params === null) {
            // No state was added, check if the URL contains parameters
            queryString = window.location.search.substring(1);
            params = parseQueryString(queryString);
        }

        if (params) {
            // If there are some parameters, fill the form with those params
            // and run the search and show results
            queryString = $.param(params, true);
            showResults(resultsURL + '?' + queryString);
            params = getFilteredParams(params);
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

    facetsInput.select2();

    var queryString = window.location.search.substring(1);
    var initialParams = parseQueryString(queryString);
    if (initialParams) {
        initialParams = getFilteredParams(initialParams);
        showResults(resultsURL + '?' + queryString);
    }

    form.dynamicForm(fieldsURL, initialParams);
});
