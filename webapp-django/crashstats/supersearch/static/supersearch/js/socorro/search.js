$(function () {
    'use strict';

    // parameters
    var fieldsURL = '/search/fields/';
    var resultsURL = '/search/results/';
    var form = $('#search-form form');
    var submitButton = $('button[type=submit]', form);
    var newLineBtn = $('.new-line');
    var contentElt = $('#search_results');
    var facetsInput = $('input[name=_facets]', form);
    var columnsInput = $('input[name=_columns_fake]', form);
    var optionsElt = $('fieldset.options', form);

    // From http://stackoverflow.com/questions/5914020/
    function padStr(i) {
        return (i < 10) ? "0" + i : "" + i;
    }

    function parseQueryString(queryString) {
        var params = {};
        var queries;
        var temp;
        var i;
        var len;

        // Split into key/value pairs
        queries = queryString.split("&");
        len = queries.length;

        if (len === 1 && queries[0] === '') {
            return false;
        }

        // Convert the array of strings into an object
        for (i = 0; i < len; i++) {
            temp = queries[i].split('=');
            var key = temp[0];
            var value = decodeURIComponent(temp[1]);
            value = value.replace('+', ' ', 'g');

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
        try {
            contentElt.tabs('destroy');
        }
        catch (e) {}
        contentElt.empty().append($('<div>', {'class': 'loader'}));

        $.ajax({
            url: url,
            success: function(data) {
                contentElt.empty().append(data).tabs();
                $('.tablesorter').tablesorter();

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

    submitButton.click(function (e) {
        e.preventDefault();
        var i;
        var len;

        var params = form.dynamicForm('getParams');

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

    facetsInput.select2({
        'data': window.FACETS,
        'multiple': true
    });
    columnsInput.select2({
        'data': window.COLUMNS,
        'multiple': true
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
        $('h4 span', optionsElt).toggle();
    });
    $('h4 + div', optionsElt).hide();

    var queryString = window.location.search.substring(1);
    var initialParams = parseQueryString(queryString);
    if (initialParams) {
        initialParams = getFilteredParams(initialParams);
        showResults(resultsURL + '?' + queryString);
    }
    else {
        // By default, add the current date to the parameters
        var now = new Date();
        var nowStr = '<=' +
                     padStr(now.getUTCFullYear()) + '-' +
                     padStr(now.getUTCMonth() + 1) + '-' +
                     padStr(now.getUTCDate()) + ' ' +
                     padStr(now.getUTCHours()) + ':00:00';

        initialParams = {
            date: nowStr
        };
    }

    form.dynamicForm(fieldsURL, initialParams, '#search-params-fieldset');
});
