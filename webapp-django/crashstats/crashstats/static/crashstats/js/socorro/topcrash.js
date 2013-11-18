/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/*jslint browser:true, regexp:false, plusplus:false, jQuery:false */
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

    /**
     * Set the Ajax spinner into the container specified by ctx.
     * @param {Object} ctx - The container into which to inject the spinner.
     */
    function showLoader(ctx) {
        var spinnerContainer = document.createElement('div');
        var spinner = document.createElement('img');

        // id for JS, class for CSS
        spinnerContainer.setAttribute('id', 'sh-ajax-loader');
        spinnerContainer.setAttribute('class', 'ajax-loader-container');
        spinner.setAttribute('src', window.SocImg + 'ajax-loader.gif');
        spinner.setAttribute('alt', 'Loading Graph');

        spinnerContainer.appendChild(spinner);
        ctx.append(spinnerContainer);
    }

    /**
     * Remove the Ajax spinner set by showLoader().
     */
    function removeLoader(ctx) {
        $('#sh-ajax-loader', ctx).remove();
    }

    /**
     * Set the Ajax spinner into the container specified by ctx.
     * @param {Object} ctx - The container into which to inject the spinner.
     * @param {string} msg - The message to display to the user.
     * @param {string} type - The type of message, can be one of info, warn or error.
     */
    function showNotification(ctx, msg, type) {
        var messageContainer = document.createElement('p');
        var message = document.createTextNode(msg);

        messageContainer.setAttribute('class', 'notification ' + type);
        messageContainer.appendChild(message);

        ctx.append(messageContainer);
    }

    /**
     * Remove the user message set by showNotification().
     */
    function removeNotification(ctx) {
        ctx.find('.message').remove();
    }

    $("#signatureList .graph-icon, #peros-tbl .graph-icon").click(function (event) {
        event.preventDefault();

        var ctx = $(this).parents('.signature-column'),
            sig = ctx.find('input').val(),
            graphContainer = ctx.find('.sig-history-container'),
            graph = ctx.find('.sig-history-graph'),
            legend = ctx.find('.sig-history-legend');

        showLoader(ctx);

        $.getJSON(window.SocAjax + window.SocAjaxStartEnd + encodeURIComponent(sig), function (data) {
            var options = {
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

            // If we have data for at least one of the properties, draw the graph
            if(data.counts.length && data.percents.length) {
                graphContainer.removeClass('hide');
                removeLoader(ctx);

              $.plot(graph,
                 [{ data: data.counts,   label: 'Count',  yaxis: 1},
                  { data: data.percents, label: 'Percent',   yaxis: 2}],
                 options);
            } else {
              removeLoader(ctx);
              showNotification(ctx, 'No data available for graph', 'info');
            }
        }).fail(function(jqXHR, textStatus, errorThrown) {
            var message = 'There was an error while processing the request.';

            if (textStatus) {
                message += ' The status of the error is: ' + textStatus;
            }

            if (errorThrown) {
                message += ' The error thrown was: ' + errorThrown;
            }

            removeLoader(ctx);
            showNotification(ctx, message, 'error');
        });
    });

    // on click close the current graph
    $(".graph-close").click(function(event) {
        event.preventDefault();
        var currentCtx = $(this).parents(".signature-column");

        currentCtx.find(".sig-history-container").addClass("hide");
    });

    /* Initialize things */
    Correlations.init();
});
