/* jshint jquery:true, strict: true */

var SignatureSummary = (function() {
    'use strict';
    var loaded = null;

    return {
        activate: function() {
            if (loaded) {
                return;
            }
            var deferred = $.Deferred();
            var $panel = $('#sigsummary');
            var url = $panel.data('url');
            $panel.on('click', '.signature-summary caption', function(event) {
                $(this).parent('table').toggleClass('initially-hidden');
            });

            $.get(url)
            .done(function(html) {
                $('.signature-summary', $panel).html(html);
                $('.sig-dashboard-tbl', $panel).show();
                deferred.resolve();
            })
            .fail(function() {
                $('.loading-failed', $panel).show();
                deferred.reject.apply(deferred, arguments);
            })
            .always(function() {
                $('.loading-placeholder', $panel).hide();
            });

            loaded = true;
            return deferred.promise();
        }
    };
})();


Panels.register('sigsummary', function() {
    'use strict';
    return SignatureSummary.activate();
});
