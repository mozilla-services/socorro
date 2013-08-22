/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/*jslint browser:true, regexp:false, plusplus:false */
/*global window, $, socSortCorrelation, SocReport */

var Correlations = (function() {

    // a hash table (for uniqueness)
    var osnames = {};
    // the different types of correlation reports
    var correlations = ['core-counts', 'interesting-addons',
                        'interesting-modules'];
    // a hash table where we keep all unique signatures that have correlations
    var all_signatures = {};

    function loadCorrelations(type, callback) {
        var url = SocReport.sig_base + '?correlation_report_type=' + type +
                  '&' + SocReport.path + '&platforms=';
        var data = {
            correlation_report_type: type,
            product: SocReport.product,
            version: SocReport.version
        };
        // osnames is a dictionary so...
        data.platforms = $.map(osnames, function(i, osname) {
            return osname;
        }).join(',');

        $.getJSON(SocReport.sig_base, data, function (json) {
            $.each(json.hits, function(i, sig) {
                all_signatures[sig] = 1;
            });
            if (callback) callback();
        });
    }

    function expandCorrelation($element) {
        var row = $element.parents('tr');
        $('.correlation-cell .top span', row).html(SocReport.loading);
        var osname = row.find('.osname').text();
        var signature = row.find('.signature').attr('title');
        var data = {
            platform: osname,
            signature: signature,
            product: SocReport.product,
            version: SocReport.version
        };
        var types_done = 0;
        $.each(correlations, function(i, type) {
            data.correlation_report_type = type;
            $.getJSON(SocReport.base, data, function(json) {
                var report = '<h3>' + json.reason + '</h3>';
                report += json.load.split("\n").join("<br>");
                row.find('.' + type).html(report);
                types_done += 1;

                if (types_done === correlations.length) {
                    $('.correlation-cell .top span', row).html('');
                    $('.correlation-cell div div.complete', row).show();
                    $element.text('Show Less');
                }
            });
        });

        return false;
    }

    function contractCorrelation($element) {
        var row = $element.parents('tr');
        $('.correlation-cell div div.complete', row).hide();
        $element.text('Show More');
        return false;
    }

    return {
       init: function() {

           // update the correlation-panel .top and .complete
           // FIXME surely we could get the osnames without trolling the DOM...
           $('td a.signature').each(function () {
               var row = $(this).parents('tr'),
                 osname = row.find('.osname').text();
               // only need a set of unique names
               osnames[osname] = 1;
           });

           // set up an expander clicker
           $('.correlation-cell a.correlation-toggler').click(function() {
               var $element = $(this);
               var was_clicked = $element.hasClass('__clicked');
               // close all expanded
               $('.__clicked').each(function() {
                   contractCorrelation($(this).removeClass('__clicked'));
               });
               if (!was_clicked) {
                   expandCorrelation($element.addClass('__clicked'));
               }
               return false;
           });

           $.ajaxSetup({
              error: function() {
                  $('.correlation-cell .top span').html('Error loading correlation report');
              }
           });

           // prepare for AJAX loading
           $('.correlation-cell .top span').html(SocReport.loading);

           // for each type of correlation start downloading all signatures that
           // have correlations
           var correlation_types_loaded = 0;
           function correlationsTypeLoaded() {
               correlation_types_loaded += 1;
               if (correlation_types_loaded === correlations.length) {
                   // all correlation types have fully called back,
                   // let's finish up things
                   //
                   $('.signature').each(function() {
                       var signature = $(this).attr('title');
                       if (all_signatures[signature] || false ) {
                           $(this).parents('tr')
                             .find('.correlation-toggler')
                               .show();
                       }
                   });

                   $('.correlation-cell .top span').html('');
               }

           }
           for (var i in correlations) {
               loadCorrelations(correlations[i], correlationsTypeLoaded);
           }

       }
    };
})();

$(document).ready(function () {
    var ranks = [],
        perosTbl = $("#peros-tbl")
        ;

    $("#signatureList").tablesorter({
        headers: {
            0: { sorter: false },
            1: { sorter: false },
            5: { sorter: 'digit' },
            6: { sorter: 'digit' },
            7: { sorter: 'digit' },
            8: { sorter: 'digit' },
            9: { sorter: 'digit' },
            11: { sorter: false },  // Bugzilla IDs
            12: { sorter: false }   // Correlation
        }
    });

    perosTbl.tablesorter({
        headers: {
            0: { sorter: false },
            1: { sorter: false },
            4: { sorter: 'text' },
            5: { sorter: 'digit' },
            6: { sorter: 'digit' },
            7: { sorter: 'digit' }
        }
    });

    $("#signatureList tr, #peros-tbl tr").each(function() {
	$.data(this, 'graphable', true);
    });
    $("#signatureList tr, #peros-tbl tr").hover(function(){
            $('.graph-icon', this).css('visibility', 'visible');
        }, function(){
            $('.graph-icon', this).css('visibility', 'hidden');
    });
    $("#signatureList .graph-icon, #peros-tbl .graph-icon").click(function (e) {
        var button = $(this),
            sig = button.parents('tr').find('input').val(),
            graph = button.parents('tr').find('.sig-history-graph'),
            legend = button.parents('tr').find('.sig-history-legend'),
            currentCtx = $(this).parents("td");

        button.get(0).disabled = true;
        legend.html("<img src='" + window.SocImg + "ajax-loader.gif' alt='Loading Graph' />");
        $.getJSON(window.SocAjax + window.SocAjaxStartEnd + encodeURI(sig), function (data) {
            currentCtx.find(".graph-close").removeClass("hide");
            graph.show();
            legend.show();
            button.hide();
            var tr = button.parents('tr'),
            options = {
                xaxis: {mode: 'time'},
                legend: {
                    noColumns: 4,
                    container: legend,
                    margin: 0,
                    labelBoxBorderColor: '#FFF'},
                series: {
                    lines: { show: true },
                    points: { show: false },
                    shadowSize: 0
                }
            };

            $.plot(graph,
               [{ data: data.counts,   label: 'Count',  yaxis: 1},
                { data: data.percents, label: 'Percent',   yaxis: 2}],
               options);
        });
	return false;
    });

    // on click close the current graph
    $(".graph-close").click(function(event) {
        event.preventDefault();
        var currentCtx = $(this).parents("td");

        currentCtx.find(".graph-close").addClass("hide");

        currentCtx.find(".sig-history-legend, .sig-history-graph").hide();
        currentCtx.find(".graph-icon").show();
    });

    /* Initialize things */
    Correlations.init();
});
