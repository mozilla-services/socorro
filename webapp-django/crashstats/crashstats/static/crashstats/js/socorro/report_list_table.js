/*jslint Panels:true */

var Table = (function() {
    var loaded = null;

    function post_activate($panel) {
        $('#buildid-table').tablesorter();
    }

    return {
       activate: function() {
           if (loaded) return;
           var deferred = $.Deferred();
           var $panel = $('#table');
           var url = $panel.data('partial-url');
           var qs = location.href.split('?')[1];
           url += '?' + qs;
           var req = $.ajax({
               url: url
           });
           req.done(function(response) {
               $('.loading-placeholder', $panel).hide();
               $('.inner', $panel).html(response);
               post_activate($panel);
               deferred.resolve();
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

Panels.register('table', function() {
    // executed every time the panel is activated
    return Table.activate();
});
