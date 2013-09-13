/*jslint Panels:true */

var Comments = (function() {
    var loaded = null;

    return {
       activate: function() {
           if (loaded) return;
           var deferred = $.Deferred();
           var $panel = $('#comments');
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
               var $tab = $('#report-list-nav a[href="#comments"] span');
               $tab.text($tab.text() + ' (' + count + ')');
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

Panels.register('comments', function() {
    // executed every time the Comments panel is activated
    return Comments.activate();
});
