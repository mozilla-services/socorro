$(function () {
    'use strict';

    // Create the table of content.
    var tableOfContent = $('<ol>');
    var currentContainer = tableOfContent;

    $('h1[id], h2[id]', '.body').map(function (i, elem) {
        var listItem = $('<li>');
        listItem.append($('<a>', { href: '#' + elem.id, text: elem.innerText }));
        if (elem.localName == 'h1') {
            tableOfContent.append(listItem);
            currentContainer = $('<ol>');
            listItem.append(currentContainer);
        }
        else {
            currentContainer.append(listItem);
        }
    });

    $('#table-of-content').append(tableOfContent).show();

    // Add a command to all examples.
    $('.example pre code').prepend('"').prepend(
        $('<span>', { text: 'curl ' }).addClass('http-verb')
    ).append('"');

    // JSON results viewers.
    $('.example pre code').each(function () {
        var $code = $(this);
        var $example = $code.parent().parent();
        var url = $code.data('url');

        // Add a "try it" button to each individual example URL
        // (there can be several URLs per example).
        $code.append($('<button>', { text: 'try it' })
            .addClass('try')
            .click(function () {
                // Remove any previous results.
                $('.results', $example).remove();

                // Create a new results container.
                var resultsViewer = $('<div>').addClass('results');
                $example.append(resultsViewer);

                // Add a title and a hide button.
                var hideBtn = $('<span>', { text: 'x' })
                    .addClass('hide')
                    .click(function () {
                        $('.results', $example).remove();
                    });

                resultsViewer.append(
                    $('<h2>', { text: 'Results', title: 'Results for ' + url })
                    .append(hideBtn)
                );

                // Add a container for the JSON data, and give it a loader.
                var jsonContent = $('<div>').append($('<div>').addClass('loader'));
                resultsViewer.append(jsonContent);

                // Now load the data and we have it, show it nicely.
                $.getJSON(url, function (data) {
                    jsonContent.JSONView(data);
                });
            })
        );
    });
});
