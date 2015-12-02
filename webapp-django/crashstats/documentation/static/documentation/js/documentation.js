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
});
