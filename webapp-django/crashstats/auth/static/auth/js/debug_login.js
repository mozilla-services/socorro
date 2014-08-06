$(function() {
    'use strict';

    function drawConclusion() {
        if ($('.verdict.bad').length) {
            $('.conclusion.bad').show();
        } else {
            $('.conclusion.good').show();
        }
    }
    var soon;
    function drawConclusionSoon() {
        if (soon) {
            clearTimeout(soon);
        }
        soon = setTimeout(drawConclusion, 1000);
    }

    function addVerdict(container, msg, color) {
        container.append(
            $('<p>').addClass('verdict').html(msg).addClass(color)
        );
    }

    /* Check that the session cookie secure variable matches what is
       being used. */
    var cookie_secure = $('#session-cookie-secure');
    if (cookie_secure.data('session-cookie-secure')) {
        // then you better be on HTTPS actually
        if (location.protocol === 'http:') {
            // bad
            addVerdict(
                cookie_secure,
                "You're using <b>HTTP</b> but SESSION_COOKIE_SECURE set to true!",
                'bad'
            );
        } else {
            // fine
            addVerdict(
                cookie_secure,
                "You're using <b>HTTPS</b> and SESSION_COOKIE_SECURE set to true.",
                'good'
            );
        }
    } else {
        // then you better on HTTP
        if (location.protocol === 'http:') {
            addVerdict(
                cookie_secure,
                "You're using <b>HTTP</b> right now which is expected.",
                'good'
            );
        } else {
            addVerdict(
                cookie_secure,
                "You're using <b>HTTPS</b> but SESSION_COOKIE_SECURE set to false!.",
                'bad'
            );
        }
    }
    $.getJSON(location.pathname, {'test-cookie': true})
    .done(function(r) {
        if (r.cookie_value === cookie_secure.data('cookie-value')) {
            addVerdict(
                cookie_secure,
                "Happily able to set a cookie and retrieving it again.",
                'good'
            );
        } else {
            addVerdict(
                cookie_secure,
                "Unable to set a cookie and retrieving it again.",
                'bad'
            );
        }

    }).fail(function() {
        console.warn('Unable to make an AJAX request to test cookies');
        console.error(arguments);
        $('#check-console').show();
    }).always(function() {
        $('.loading', cookie_secure).hide();
        drawConclusionSoon();
    });

    /* Check that caching works */
    var caching = $('#caching');
    $.getJSON(location.pathname, {'test-caching': true})
    .done(function(r) {
        if (r.cache_value === caching.data('cache-value')) {
            // seems to work
            addVerdict(
                caching,
                'Setting and retrieving from cache seems to work.',
                'good'
            );
        } else {
            addVerdict(
                caching,
                'Unable to set a value in cache that sticks! ' +
                'Check your <code>settings.CACHES</code> settings.',
                'bad'
            );
        }
    }).fail(function() {
        console.warn('Unable to make an AJAX request');
        console.error(arguments);
        $('#check-console').show();
    }).always(function() {
        $('.loading', caching).hide();
        drawConclusionSoon();
    });

    /* Check that including the browserid .js files worked */
    var browserid_js = $('#browserid-js');
    if (window.django_browserid) {
        addVerdict(
            browserid_js,
            "The 'browserid/api.js' file appears to have loaded.",
            'good'
        );
    } else {
        addVerdict(
            browserid_js,
            "The 'browserid/api.js' file appears to <b>not</b> have loaded.",
            'bad'
        );
    }

    /* Check that the BROWSERID_AUDIENCES matches */
    var browserid_audiences = $('#browserid-audiences');
    var debug = browserid_audiences.data('debug');
    var audiences = browserid_audiences.data('audiences');
    if (audiences.length) {
        // necessary because `"".split(',')` becomes `[""]`
        audiences = audiences.split(',');
    } else {
        audiences = [];
    }

    function matchesCurrentOrigin(url) {
        var a = document.createElement('a');
        a.href = url;
        var hostMatch = !a.host || window.location.host === a.host;
        var protocolMatch = !a.protocol || window.location.protocol === a.protocol;
        return hostMatch && protocolMatch;
    }
    if (audiences) {
        // at least one of them needs to match the current protocol + hostname
        var matched = false;
        audiences.forEach(function(each) {
            if (matchesCurrentOrigin(each)) {
                matched = true;
            }
        });
        if (matched) {
            addVerdict(
                browserid_audiences,
                'The current URL matches one of the values in ' +
                '<code>BROWSERID_AUDIENCES</code>. ',
                'good'
            );
        } else {
            addVerdict(
                browserid_audiences,
                'No value in your <code>BROWSERID_AUDIENCES</code> setting appears ' +
                "to match the current URL you're using. ",
                'bad'
            );
        }
    } else if (!debug) {
        addVerdict(
            browserid_audiences,
            "You're not in DEBUG mode but you have not set up the " +
            "<code>BROWSERID_AUDIENCES</code> setting.",
            'bad'
        );
    } else {
        addVerdict(
            browserid_audiences,
            "You're in DEBUG mode so you do NOT need to set up " +
            "<code>BROWSERID_AUDIENCES</code>",
            'good'
        );
    }

    /* Check that the home page has the necessary DOM elements */
    var browserid_dom = $('#browserid-dom');
    $.ajax({
        url: '/',
        dataType: 'html'
    }).done(function(response) {
        if (response.indexOf('id="browserid-info"') > -1) {
            addVerdict(
                browserid_dom,
                'Home page has a <code>id="browserid-info"</code> element',
                'good'
            );
        } else {
            addVerdict(
                browserid_dom,
                'No element with <code>id="browserid-info"</code> on the home page',
                'bad'
            );
        }
        if (response.indexOf('browserid-logout') > -1 ||
            response.indexOf('browserid-login') > -1) {
            addVerdict(
                browserid_dom,
                "Found a browserid-login or browserid-logout element on the home page",
                'good'
            );
        } else {
            addVerdict(
                browserid_dom,
                "Can't find a browserid-login or browserid-logout element on the home page",
                'bad'
            );
        }
    }).fail(function() {
        console.warn('Unable to make an AJAX request');
        console.error(arguments);
        $('#check-console').show();
    }).always(function() {
        $('.loading', browserid_dom).hide();
        drawConclusionSoon();
    });


});
