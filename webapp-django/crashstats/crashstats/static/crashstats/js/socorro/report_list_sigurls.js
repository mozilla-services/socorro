/*jslint Panels:true */

var SignatureURLs = (function() {
    var loaded = null;

    function post_activate($panel) {
        $('#sigurls-tbl').tablesorter();
    }

    return {
       activate: function() {
           if (loaded) return;
           var deferred = $.Deferred();
           var $panel = $('#sigurls');
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

Panels.register('sigurls', function() {
    return SignatureURLs.activate();
});
