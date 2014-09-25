/* globals Panels, $, SocReport, socSortCorrelation, accordion */

var Correlations = (function() {
    var loaded = null;

    function urlMaker(version, os) {
        var url = SocReport.base ;
        url += '?product=' + SocReport.product;
        url += '&version=' + version;
        url += '&platform=' + os;
        url += '&signature=' + SocReport.signature;
        return function makeUrl(type) {
            return url + '&correlation_report_type=' + type;
        };
    }

    /**
     * Populates the panel specified by type.
     * @param {string} type - The correlation type
     * @param {object} data - The data to populate the panel with.
     */
    function populatePanel(type, data) {
        var contentContainer = $('#' + type + '-correlation');
        var noData = $('<p />', { text: 'No correlation data found.' });

        if(data) {
            var panelHeading = $('<h3 />', {
                text: data.reason
            });
            // first separate the data into individual 'rows'
            var dataRows = data.load.split(/\n/);

            if (dataRows.length > 1) {
                var table = $('<table />', {
                    class: 'data-table'
                });
                var thead = $('<thead />');
                var headerRow = $('<tr />');
                // a little work left to be done on the type header
                var headers = ['All Crashes For OS', 'All Crashes For Signature', type];

                $(headers).each(function(index, header) {
                    headerRow.append($('<th />', {
                        text: header
                    }));
                });
                table.append(thead).append(headerRow);

                // loop through the lines and remove the vs. bits and split the
                // string into 3 'columns' per 'row'. Create the table rows and
                // attach them to the table.
                $(dataRows).each(function(index, row) {
                    var tableRow = $('<tr />');
                var columns = row.replace(/\svs\.\s/, '').split(/(?:\)\s+)/);
                    $(columns).each(function(index, column) {
                        tableRow.append($('<td />', {
                            text: column
                        }));
                    });
                    table.append(tableRow);
                });

                contentContainer.empty().append([panelHeading, table]);
                socSortCorrelation('#' + type + '_correlation');
            }
            // guard against empty records that sometimes gets returned.
            else if (dataRows.length === 1 && dataRows[0] === '') {
                // there seemed to be data but alas, it was an empty promise.
                contentContainer.empty().append(noData);
            }
        } else {
            contentContainer.empty().append(noData);
        }
    }

    // Load correlation data for various types.
    // @types CPU, Add-On, Module
    function loadCorrelationTabData(version, os, deferred) {
        var makeUrl = urlMaker(version, os);
        var types = ['core-counts', 'interesting-addons', 'interesting-modules'];

        function loadByType(type) {
            $.getJSON(makeUrl(type), function(data) {

                populatePanel(type, data);

            }).fail(function(jqXHR, textStatus, errorThrown) {
                var msg = errorThrown;
                if (jqXHR.responseText !== '') {
                    msg += ': ' + jqXHR.responseText;
                }

                $('#' + type + '-correlation').html(msg);
            });
        }

        while (true) {
            var type = types.shift();
            if (!type) {
                // all types done
                deferred.resolve();
                break;
            }
            loadByType(type);
        }
    }


    return {
       activate: function() {
           if (loaded) return;
           var deferred = $.Deferred();
           var $panel = $('#correlations');
           var url = $panel.data('partial-url');
           var qs = location.href.split('?')[1];
           url += '?' + qs;
           var req = $.ajax({
               url: url
           });
           req.done(function(response) {
               $('.loading-placeholder', $panel).hide();
               $('.inner', $panel).html(response);
               var $wrapper = $('.correlations-wrapper', $panel);
               var version = $wrapper.data('correlation_version');
               var os = $wrapper.data('correlation_os');

               accordion.init(document.querySelector('.accordion'));

               $('button.load-version-data').click(function () {
                   var type = $(this).attr('name');
                   var makeUrl = urlMaker(version, os);
                   var spinner = $('<img />', {
                      id: 'loading-spinner',
                      src: '/static/img/loading.png',
                      width: '16',
                      height: '17',
                      alt: 'loading spinner'
                   });
                   var loader = $('<p />', {
                       text: 'Loading '
                   }).append(spinner);
                   var contentPanel = $('#' + type + '-correlation');

                   contentPanel.empty().append(loader);

                   $.getJSON(makeUrl(type), function(data) {
                       populatePanel(type, data);
                  }).fail(function(jqXHR, textStatus, errorThrown) {
                      var msg = errorThrown;
                      if (jqXHR.responseText !== '') {
                          msg += ': ' + jqXHR.responseText;
                      }

                      $('#' + type + '-correlation').html(msg);
                  });
               });

               if (version && os) {
                   loadCorrelationTabData(version, os, deferred);
               }
           });
           req.fail(function(data, textStatus, errorThrown) {
               $('.loading-placeholder', $panel).hide();
               $('.loading-failed', $panel).show();
               deferred.reject(data, textStatus, errorThrown);
           });
           loaded = true;
           return deferred.promise();
       }
    };
})();

Panels.register('correlations', function() {
    return Correlations.activate();
});
