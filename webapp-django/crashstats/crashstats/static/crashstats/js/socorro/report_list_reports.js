/*jslint window:true Panels:true */

var Reports = (function() {
    var loaded = null;

    return {
       activate: function() {
           if (loaded) return;
           var deferred = $.Deferred();
           var $panel = $('#reports');
           var url = $panel.data('partial-url');
           var qs = location.href.split('?')[1];
           url += '?' + qs;
           var req = $.ajax({url: url});
           req.done(function(response) {
               $('.loading-placeholder', $panel).hide();
               $('.inner', $panel).html(response);
               deferred.resolve();
           });
           req.fail(function(data, textStatus, errorThrown) {
               deferred.reject(data, textStatus, errorThrown);
           });
           loaded = true;
           return deferred.promise();
       }
    };
})();

Panels.register('reports', function() {
    // executed every time the Reports panel is activated
    return Reports.activate();
});
