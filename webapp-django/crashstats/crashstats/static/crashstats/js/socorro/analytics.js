/*global ga */

var Analytics = (function() {
    'use strict';

    function wrap() {
        if (typeof ga !== 'undefined') {
            ga.apply(undefined, arguments);
        }
    }

    return {
        trackTabSwitch: function(page, id) {
            wrap('send', 'event', 'tab', page, id);
        },
        trackPageview: function(url) {
            wrap('send', 'pageview', url);
        }
    };
})();
