/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/*jslint browser:true, regexp:false, plusplus:false */
/*global window, $, socSortCorrelation, SocReport */
$(document).ready(function () {
    var osnames = {},
        signatures = [],
        ranks = [],
        expandCorrelation,
        contractCorrelation,
        loadCorrelations,
        correlationsLoaded,
        correlationCallback,
        i,
        perosTbl = $("#peros-tbl"),
        correlations = ['core-counts', 'interesting-addons',
                        'interesting-modules'];

    $("#signatureList").tablesorter({
        headers: {
            0: { sorter: false },
            1: { sorter: false },
            5: { sorter: 'digit' },
            6: { sorter: 'digit' },
            7: { sorter: 'digit' },
            8: { sorter: 'digit' },
            9: { sorter: 'digit' }
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

    // Grab the div.rank....
    // update the correlation-panel1 .top and .complete
    // FIXME surely we could get the osnames without trolling the DOM...
    $('td a.signature').each(function () {
        var row = $(this).parents('tr'),
            osname = row.find('.osname').text(),
            rank = row.find('td.rank').text();

        // only need a set of unique names
        osnames[osname] = 1;
        ranks.push(rank);
    });

    expandCorrelation = function () {
        var row = $(this).parents('tr');
        $('.correlation-cell div div.complete', row).show();
        /* $('.correlation-cell div', row).removeClass('correlation-preview');*/
        $.each(correlations, function(k,type) {
            var osname = row.find('.osname').text();
            var signature = row.find('.signature').text();
            var url = SocReport.base + '?correlation_report_type=' + type +
                      '&' + SocReport.path + '&platform=' + encodeURI(osname) +
                      '&signature=' + signature;

            $.getJSON(url, {type: type}, function(json) {
                var report = '<h3>' + json.reason + '</h3>';
                report += json.load.split("\n").join("<br>");
                row.find('.' + type).append(report);
            });
        });

        $(this).text('Show Less');
        return false;
    };

    contractCorrelation = function () {
        var row = $(this).parents('tr');
        $('.correlation-cell div div.complete', row).hide();
        $(this).text('Show More');
        return false;
    };
    loadCorrelations = function (type, callbackFn) {
        var i,
            panel;
        $('.correlation-cell .top span').html(SocReport.loading);
        $('.correlation-cell .correlation-toggler').toggle(expandCorrelation, contractCorrelation);

        $.ajaxSetup({
            error: function() {
                $('.correlation-cell .top span').html('Error loading correlation report');
            }
        });
        $.each(osnames, function(osname) {
            $.getJSON(SocReport.sig_base + '?correlation_report_type=' + type +
                      '&' + SocReport.path + '&platforms=' + encodeURI(osname),
            function (json) {
                $('.correlation-cell .top span').html('');
                $.each(json.hits, function(i, sig) {
                    var sig = json.hits[i];
                    $('.signature').each(function() {
                        if (sig == $(this).attr('title')) {
                            $(this).parents('tr')
                                   .find('.correlation-toggler')
                                   .show();
                        }
                    });
                });
                callbackFn();
            });
        });
    };

    correlationsLoaded = 0;
    correlationCallback = function () {
        var i,
            captureRankFn = function (rank) {
                    return function () {
                        var panel = '#correlation-panel' + rank,
                            highest;

                        window.socSortCorrelation(panel);
                        highest = window.socDetermineHighestCorrelation(panel);
                        $('.top span', panel).text(highest);

                        if (highest.indexOf('UNKNOWN') === 0) {
                            $('.correlation-toggler', panel).remove();
                        } else {
                            // Make these guys presentable.... add span tag for girdle
                            $('pre', panel).each(function () {
                                var corr = $(this).text(),
                                    parts = corr.split('\n'),
                                    newCorr;
                                newCorr = $('<div class="correlation-line"><pre>' + corr + '</pre></div>');
                                newCorr.girdle({previewClass: 'correlation-module-preview', fullviewClass: 'correlation-module-popup'});
                                $(this).replaceWith(newCorr);
                            });
                        }
                    };
                };//captureRankFn
        correlationsLoaded++;

        if (correlationsLoaded >= correlations.length) {
            // Sort and display

            for (i = 0; i < ranks.length; i++) {
	        //TODO left off here - make an 'makeUpdateRowFn' function...


                setTimeout(captureRankFn(ranks[i]), 100);
            }//end for
        }//end if
    };//end correlationCallback

    /* ensure there are correlations to load before calling the function */
    if($('.correlation-cell').length > 0) {
        for (i = 0; i < correlations.length; i++) {
            loadCorrelations(correlations[i], correlationCallback);
        }
    }
});
