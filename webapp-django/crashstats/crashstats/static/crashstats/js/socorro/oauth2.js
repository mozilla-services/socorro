var OAuth2 = (function() {
    /* Generally the best documentation for working with GoogleAuth
    is here: https://developers.google.com/identity/sign-in/web/reference
    The introduction is here:
    https://developers.google.com/identity/sign-in/web/sign-in
    */

    var client_id = document.head.querySelector(
        'meta[name="google-signin-client_id"]'
    ).content;

    var GoogleAuth = null;

    var loadGoogleAuth = function() {
        return new Promise(function(resolve, reject) {
            if (!GoogleAuth) {
                gapi.auth2.init();
                GoogleAuth = gapi.auth2;
            }
            // If you instead try to do:
            // resolve(GoogleAuth.getAuthInstance()) here inside
            // this promise body your browser will crash. Both
            // Firefox and Chrome.
            resolve(GoogleAuth);
        });
    };

    var serverSignout = function() {
        var signoutURL = $('a.google-signout').attr('href');
        var csrfmiddlewaretoken = $(
            'input[name="csrfmiddlewaretoken"]'
        ).val();
        var data = {
            csrfmiddlewaretoken: csrfmiddlewaretoken,
        };
        $.post(signoutURL, data)
        .done(function() {
            document.location.reload();
        })
        .fail(function() {
            // XXX Need to understand what the conditions might be for
            // failing.
            console.warn('Failed to sign out on the server');
            console.error.apply(console, arguments);
        });
    };

    var signOut = function() {
        loadGoogleAuth()
        .then(function(auth2api) {
            var auth2 = auth2api.getAuthInstance();
            auth2.then(function() {
                auth2.signOut().then(serverSignout);
            });
        })
        .catch(function() {
            console.error.apply(console, arguments);
        });
    };

    return {
        init: function() {
            // The "signin" meta tag, and its value being "signout"
            // means that the server thinks the user has been logged in
            // to be safe.
            var signedin = document.head.querySelector(
                'meta[name="signin"]'
            );
            if (signedin && signedin.content === 'signout') {
                console.warn('Login session has to expire.');
                // You have to sign out
                signOut();
            }

            // On our HTML, we render a Sign Out link, in HTML, if the
            // the user is signed in.
            // If the Sign Out link is not there, let's instead
            // render the Sign In button.
            if ($('a.google-signout').length) {
                // Set up the sign-out button
                $('a.google-signout').on('click', function(event) {
                    event.preventDefault();
                    signOut();
                });
            } else {
                // See https://developers.google.com/identity/sign-in/web/reference
                // (scroll to gapi.signin2.render)
                // Below, some of the options have deliberately left
                // commented out for the sake of showing what can be set.
                gapi.signin2.render('signin2', {
                    // 'scope': 'profile email',
                    'scope': 'email',
                    // 'scope': 'openid',
                    // 'width': 240,
                    // 'height': 36,
                    'height': 30,
                    // 'longtitle': true,
                    // 'theme': 'dark',
                    'onsuccess': function(googleUser) {
                        var id_token = googleUser.getAuthResponse().id_token;

                        var url = $('.google-signin').data('signin-url');
                        var csrfmiddlewaretoken = $(
                            'input[name="csrfmiddlewaretoken"]'
                        ).val();
                        var data = {
                            token: id_token,
                            csrfmiddlewaretoken: csrfmiddlewaretoken,
                        };
                        $.post(url, data)
                        .done(function(response) {
                            // It worked!
                            // TODO: https://bugzilla.mozilla.org/show_bug.cgi?id=1283296
                            document.location.reload();
                        })
                        .fail(function(xhr) {
                            console.error(xhr);
                            var auth2 = gapi.auth2.getAuthInstance();
                            auth2.signOut().then(function() {
                                alert(
                                    'Signed in to Google, but unable to ' +
                                    'sign in on the server. (' +
                                    xhr.responseText + ')'
                                );
                            });
                        });
                    },
                    'onfailure': function(error) {
                        // Happens if the user,
                        // for some reason presses the "Deny" button.
                        // If that happens, there's not much to do.
                        console.error(error);
                        console.warn.apply(console, arguments);
                    }
                });

            }
        },
    };
})();


// This is how we load the google APIs, with a callback.
window.googleAPILoaded = OAuth2.init;
