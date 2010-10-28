/*jslint browser:true, regexp:false, plusplus:false */ 
/*global window, $, socSortCorrelation, SocReport */
$(document).ready(function () { 
    var osnames = [],
        signatures = [],
        ranks = [],
        expandCorrelation,
        contractCorrelation,
        loadCorrelations,
        correlations,
        correlationsLoaded,
        correlationCallback,
        i;

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
    $("#signatureList tr").each(function() {
	$.data(this, 'graphable', true);
    });
    $("#signatureList tr").hover(function(){
            $('.graph-icon', this).css('visibility', 'visible');
        }, function(){
            $('.graph-icon', this).css('visibility', 'hidden');
    });
      $("#signatureList .graph-icon").click(function (e) {
        var button = $(this),
            sig = button.parents('tr').find('input').val(),
            graph = button.parents('tr').find('.sig-history-graph'),
            legend = button.parents('tr').find('.sig-history-legend');
        button.get(0).disabled = true;
        legend.html("<img src='" + window.SocImg + "ajax-loader.gif' alt='Loading Graph' />");

        $.getJSON(window.SocAjax + encodeURI(sig) + window.SocAjaxStartEnd, function (data) {
            graph.show();
	    button.remove();
            var tr = button.parents('tr');
            $.plot(graph,
               [{ data: data.counts,   label: 'Count',  yaxis: 1},
                { data: data.percents, label: 'Percent',   yaxis: 2}],
               {//options
                xaxis: {mode: 'time'},
                legend: {container: legend, margin: 0, labelBoxBorderColor: '#FFF'},
                series: {
                    lines: { show: true },
                    points: { show: true }
                }
            });
        });
	return false;
    });

    // Grab the div.rank....
    // Grab the signature
    // update the correlation-panel1 .top and .complete
    $('td a.signature').each(function () {
        var row = $(this).parents('tr'),
            osname = row.find('.osname').text(),
            sig = $(this).text(),
            rank = row.find('td.rank').text();

        osnames.push(osname);
        signatures.push(sig);   
        ranks.push(rank);            
    });

    $('td a.signature').girdle({previewClass: 'signature-preview', fullviewClass: 'signature-popup'});
    expandCorrelation = function () {
        var row = $(this).parents('tr');
        $('.correlation-cell div div.complete', row).show();
       /* $('.correlation-cell div', row).removeClass('correlation-preview');*/
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
        
        $.post(SocReport.base + type + SocReport.path,
           {'osnames[]': osnames, 'signatures[]': signatures, 'ranks[]': ranks},
           function (json) {
                for (i = 0; i < json.length; i++) {
                    panel = '#correlation-panel' + json[i].rank;
                    $('.' + type + 's',  panel).html(json[i].correlation);
                }
                callbackFn();
            }, 
           'json');
    };

    correlations = ['cpu', 'addon', 'module'];
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
    
    for (i = 0; i < correlations.length; i++) {
        loadCorrelations(correlations[i], correlationCallback);
    }

    $('.top').girdle({previewClass: 'correlation-preview', fullviewClass: 'correlation-popup'});
});
