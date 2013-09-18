/*jslint Panels:true */

var Bugzilla = (function() {
    var loaded = null;

    return {
       activate: function() {
           if (loaded) return;
           var deferred = $.Deferred();
           var $panel = $('#bugzilla');
           var url = $panel.data('partial-url');
           var qs = location.href.split('?')[1];
           url += '?' + qs;
           var req = $.ajax({
               url: url
           });
           req.done(function(response) {
               $('.loading-placeholder', $panel).hide();
               $('.inner', $panel).html(response);
               var $wrapper = $('.wrapper', $panel);
               var count = $wrapper.data('count');
               var $tab = $('#report-list-nav a[href="#bugzilla"] span');
               $tab.text($tab.text() + ' (' + count + ')');
               if (BugLinks) {
                   // now that the HTML has been loaded,
                   // now we can let BugLinks loose on the HTML to convert
                   // bug links to something more useful
                   BugLinks.transform_with_data();
                   BugLinks.fetch_without_data();
               }
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

Panels.register('bugzilla', function() {
    // executed every time the panel is activated
    return Bugzilla.activate();
});
