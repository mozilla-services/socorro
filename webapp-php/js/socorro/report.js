/*jslint browser:true, regexp:false */
/*global window, $, socSortCorrelation, SocReport */
$(document).ready(function () {
    $('#report-index > ul').tabs({ selected: 0 });
    // See also correlation.js which uses these tabs
    var shouldLoadCPU = true,
        t;

    $('#report-index > ul li a').click(function () {
        if (shouldLoadCPU) {
            shouldLoadCPU = false;
            $('#cpu_correlation').load(SocReport.base + 'cpu' + SocReport.path,       function () {
                socSortCorrelation('#cpu_correlation');
            });
            $('#addon_correlation').load(SocReport.base + 'addon' + SocReport.path,   function () {
                socSortCorrelation('#addon_correlation');
            });
            $('#module_correlation').load(SocReport.base + 'module' + SocReport.path, function () {
                socSortCorrelation('#module_correlation');
            });
        }
    });
    $('button.load-version-data').click(function () {
        t = $(this).attr('name');
        $('#' + t + '-panel').html(SocReport.loading)
                                     .load(SocReport.base + t + SocReport.path);
    });

    $('#showallthreads').removeClass('hidden').click(function () {
        $('#allthreads').toggle(400);
        return false;
    });
    $('.signature-column').append(' <a class="expand" href="#">[Expand]</a>');
    $('.expand').click(function () {
        // swap cell title into cell text for each cell in this column
        $("td:nth-child(3)", $(this).parents('tbody')).each(function () {
            $(this).text($(this).attr('title')).removeAttr('title');
        });
        $(this).remove();
        return false;
    });
    $('#modules-list').tablesorter({sortList: [[1, 0]], headers: {1: {sorter : 'digit'}}});
});
