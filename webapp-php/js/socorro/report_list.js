/*jslint browser:true */ 
/*global socSortCorrelation, SocReport, $*/
$(document).ready(function () {
    var shouldLoadCPU = true;
    $('#report-list-nav li a').click(function () {
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
        var t = $(this).attr('name');
        $('#' + t + '-panel').html(SocReport.loading)
                                     .load(SocReport.base + t + SocReport.path);
    });
    $('#buildid-table').tablesorter(); 
    $('#reportsList').tablesorter(
        { textExtraction: 'complex' },
        { sortList : [[9,1]] },
        { 
          headers: {
            7: { sorter: 'digit' } 
          }
        }
    );
    $('#report-list-nav').tabs({selected: 2}).show();
});
