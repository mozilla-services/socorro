/* globals Panels, $, SocReport, socSortCorrelation */

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

    // Load correlation data for various types.
    // @types CPU, Add-On, Module
    function loadCorrelationTabData(version, os, deferred) {
        var makeUrl = urlMaker(version, os);
        var types = ['core-counts', 'interesting-addons', 'interesting-modules'];

        function loadByType(type) {
            $.getJSON(makeUrl(type), function(data) {
                if(data) {
                    $('#' + type + '_correlation').html('<h3>' + data.reason +
                        '</h3><pre>'+ data.load + '</pre>');
                    socSortCorrelation('#' + type + '_correlation');
                } else {
                    $('#' + type + '_correlation').text('No correlation data found.');
                }
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

               $('button.load-version-data').click(function () {
                   var type = $(this).attr('name');
                   var makeUrl = urlMaker(version, os);
                   $.getJSON(makeUrl(type), function(data) {
                       $('#' + type + '-panel').html('<h3>' + data.reason + '</h3><pre>' +
                                                     data.load + '</pre>');
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
