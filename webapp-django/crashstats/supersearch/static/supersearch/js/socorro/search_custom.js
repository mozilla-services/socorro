$(function () {
    'use strict';

    // parameters
    var form = $('#search-form form');
    var resultsURL = form.data('results-url');

    var submitButton = $('#search-button');
    var contentElt = $('#search_results');
    var indicesElt = $('#search_indices');
    var textareaElt = $('<textarea>', {'class': 'json-results'});
    var editorElt = $('#editor');
    var editor = null;

    // Default UI data.
    var defaultQuery = '{"query": {"match_all": {}}}';
    var possibleIndices = window.ELASTICSEARCH_INDICES;
    var defaultIndices = [
        possibleIndices[0],
        possibleIndices[1]
    ];

    // Django CSRF protection
    var csrftoken = $('input[name=csrfmiddlewaretoken]').val();

    function beautifulJSON(data) {
        return JSON.stringify(data, null, 4);
    }

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    function showResults(query, indices) {
        // show loader
        contentElt.empty().append($('<div>', {'class': 'loader'}));

        $.ajax({
            url: resultsURL,
            data: {'query': query, 'indices': indices},
            type: 'POST',
            traditional: true,
            success: function(data) {
                // Render that JSON beautiful.
                data = beautifulJSON(data);
                textareaElt.empty().val(data);
                contentElt.empty().append(textareaElt);
            },
            error: function(jqXHR) {
                var errorTitle = 'Oops, an error occured';
                var errorMsg = 'Please fix the following issues: ';

                var errorContent = $('<div>', {class: 'error'});
                errorContent.append($('<h3>', {text: errorTitle}));
                errorContent.append($('<p>', {text: errorMsg}));
                errorContent.append($('<p>', {text: jqXHR.responseText}));

                contentElt.empty().append(errorContent);
            }
        });
    }

    submitButton.click(function (e) {
        e.preventDefault();

        var query = editor.getValue();
        var indices = indicesElt.select2('val');
        var state = {
            'query': query,
            'indices': indices
        };

        window.history.pushState(state, 'Search results', window.location.pathname);
        showResults(query, indices);
    });

    window.onpopstate = function (e) {
        if (e.state) {
            // If there is a query, run the search and show results
            var query = e.state.query;
            var indices = e.state.indices;

            showResults(query, indices);
            editor.setValue(query);
            indicesElt.select2('data', indices);
        }
        else {
            // If there are no parameters, empty the form and show the default content
            editor.setValue(defaultQuery);
            indicesElt.select2('data', defaultIndices);
            contentElt.empty().append($('<p>', {'text': 'Run a search to get some results. '}));
        }
    };

    var jsonQuery = editorElt.html();
    if (!jsonQuery) {
        jsonQuery = defaultQuery;
    }
    editorElt.html(beautifulJSON(JSON.parse(jsonQuery)));

    // Prepare the ACE editor for JSON content.
    editor = ace.edit('editor');
    editor.setTheme('ace/theme/monokai');
    editor.getSession().setMode('ace/mode/json');

    indicesElt.select2({
        'data': possibleIndices,
        'closeOnSelect': false,
        'multiple': true,
        'width': 'element'
    });
    if (!indicesElt.val()) {
        indicesElt.select2('data', defaultIndices);
    }
});
