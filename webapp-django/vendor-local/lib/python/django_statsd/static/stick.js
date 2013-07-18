(function(exports) {
"use strict";
/*
 * A simpler boomerang: https://github.com/yahoo/boomerang that just
 * does navigation timing. Requires jquery.
 */

exports.send = function(url) {
    /* Sends the timing data to the given URL */
    var perf = window.performance || window.msPerformance ||
               window.webkitPerformance || window.mozPerformance;
    if (perf) {
        setTimeout(function() {
            $.post(url,  {
                'window.performance.timing.navigationStart': perf.timing.navigationStart,
                'window.performance.timing.domComplete': perf.timing.domComplete,
                'window.performance.timing.domInteractive': perf.timing.domInteractive,
                'window.performance.timing.domLoading': perf.timing.domLoading,
                'window.performance.timing.loadEventEnd': perf.timing.loadEventEnd,
                'window.performance.timing.responseStart': perf.timing.responseStart,
                'window.performance.navigation.redirectCount': perf.navigation.redirectCount,
                'window.performance.navigation.type': perf.navigation.type,
                'client': 'stick'
            });
        }, 1000);
    }
};

})(typeof exports === 'undefined' ? (this.stick = {}) : exports);



