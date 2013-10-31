/*jslint Panels:true, browser:true, jquery:true */

var SignatureURLs = (function() {
    var loaded = null;

    function post_activate($panel) {
        $('#signature-urls').tablesorter();

        // Show and truncate URLs to make copying easier
        $('.urlvis-toggle a').on('click', function(event) {
            event.preventDefault();

            var current_txt = $(this).text();
            var toggled_txt = $(this).data('toggled');

            $(this).text(toggled_txt);
            $(this).data('toggled', current_txt);

            // Find all anchor links inside the urls table
             $('#signature-urls a').each(function() {
                var link = $(this);
                var title = link.attr('title');
                var txt = link.text();

                link.attr('title', txt);
                link.text(title);
            });
        });
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
