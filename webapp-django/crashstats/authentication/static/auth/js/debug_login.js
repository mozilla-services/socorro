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

});
