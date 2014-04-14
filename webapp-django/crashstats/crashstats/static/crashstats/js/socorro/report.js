/*jslint browser:true, regexp:false */
/*global window, $, socSortCorrelation, SocReport */
$(document).ready(function () {
    $('#report-index').tabs({ selected: 0 });
    // See also correlation.js which uses these tabs
    var shouldLoadCPU = true,
        t;

    $('#report-index > ul li a').click(function () {
        if (shouldLoadCPU) {
            shouldLoadCPU = false;
            $.map(['core-counts', 'interesting-addons', 'interesting-modules'],
            function(type) {
             $.getJSON(SocReport.base + '?correlation_report_type=' + type +
                       '&' + SocReport.path, function(data) {
                $('#' + type + '_correlation').html('<h3>' + data.reason +
                    '</h3><pre>'+ data.load + '</pre>');
                    socSortCorrelation('#' + type + '_correlation');
             });
            });
        }
    });
    $('button.load-version-data').click(function () {
        t = $(this).attr('name');
        $.getJSON(SocReport.base + '?correlation_report_type=' + t +
                  '&' + SocReport.path, function(data) {
            $('#' + t + '-panel').html('<h3>' + data.reason + '</h3><pre>' +
                                       data.load + '</pre>');
        });
    });

    $('#showallthreads').removeClass('hidden').click(function () {
        $('#allthreads').toggle(400);
        return false;
    });

    var tbls = $("#frames").find("table"),
    addExpand = function(sigColumn) {
        $(sigColumn).append(' <a class="expand" href="#">[Expand]</a>');
        $('.expand').click(function(event) {
            event.preventDefault();
            // swap cell title into cell text for each cell in this column
            $("td:nth-child(3)", $(this).parents('tbody')).each(function () {
                $(this).text($(this).attr('title')).removeAttr('title');
            });
            $(this).remove();
        });
    };

    // collect all tables inside the div with id frames
    tbls.each(function() {
        var isExpandAdded = false,
        cells = $(this).find("tbody tr td:nth-child(3)");

        // Loop through each 3rd cell of each row in the current table and if
        // any cell's title atribute is not of the same length as the text
        // content, we need to add the expand link to the table.
        // There is a second check to ensure that the expand link has not been added already.
        // This avoids adding multiple calls to addExpand which will add multiple links to the
        // same header.
        cells.each(function() {
            if(($(this).attr("title").length !== $(this).text().length) && (!isExpandAdded)) {
                addExpand($(this).parents("tbody").find("th.signature-column"));
                isExpandAdded = true;
            }
        });
    });

    $('#modules-list').tablesorter({sortList: [[1, 0]], headers: {1: {sorter : 'digit'}}});
});
